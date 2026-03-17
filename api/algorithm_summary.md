# Tóm tắt thuật toán so sánh Cấu trúc 3 Màu Chủ đạo (3 Dominant Colors)

## 1. Tóm tắt những thay đổi

Dự án đã được nâng cấp cách tính "Độ tương đồng màu sắc" (Color Similarity) giữa 2 bức ảnh:

- **Trước đây (Cũ)**: Sử dụng phương pháp giao thoa biểu đồ màu *Histogram Intersection*. Phương pháp này đếm số lượng pixel của từng màu RGB độc lập trên toàn bộ ảnh ảnh rồi so sánh khoảng giao thoa, thường kém chính xác do nhiễu hạt hoặc khi vị trí màu bị thay đổi.
- **Hiện tại (Mới)**: Trích xuất ra đúng **3 màu chủ đạo** (dominant colors) của bức ảnh cùng tỷ lệ % diện tích thực tế. Khi tính độ tương đồng của 2 ảnh, hệ thống ánh xạ chéo (mapping) thông minh từng màu của ảnh A với màu gần giống nhất của ảnh B dựa trên nhãn quan thực tế.

**Các file chính đã thay đổi mã nguồn:**
- `image_processor.py`: Nơi chứa bộ não trích xuất 3 màu và toán học so sánh màu.
- `database.py` & `database_service.py`: Thêm cột lưu JSON `dominant_colors_json` vào PostgreSQL.
- `schemas.py` & `images.py`: Mở rộng API schema để xuất dữ liệu 3 màu ra frontend.

---

## 2. Luồng hoạt động (Data Flow)

### Quá trình Upload / Nhập ảnh (Import)
1. Ảnh được đọc vào và thu nhỏ về kích thước tĩnh `100x100` pixels (để tối ưu hóa tốc độ tính điểm màu).
2. Dữ liệu mảng pixel được chạy qua mô hình Machine Learning **K-Means Clustering** (với tùy chỉnh `k=3`) để phân nhóm lại thành 3 cụm màu đại diện lớn nhất.
3. Hệ thống đếm lượng pixel mỗi cụm để cho ra tỉ lệ phần trăm xuất hiện của từng màu (VD: Xanh dương 60%, Đen 30%, Trắng 10%).
4. Ánh xạ các màu này sang hệ thống mã `HEX` (ví dụ `#ffffff`) và `RGB` (ví dụ `[255,255,255]`), cập nhật vào database với định dạng JSON.

### Quá trình Tìm kiếm ảnh tương đồng (Search)
Khi có 1 bức ảnh được đưa lên làm ảnh truy vấn (Q):
1. Tính toán vector `DINOv2` và bộ 3 màu chủ đạo của ảnh Q.
2. **Giai đoạn 1 (Lọc vector sinh học):** Truy vấn siêu tốc trong cơ sở dữ liệu `PostgreSQL` (+ extension `pgvector`) dựa trên ngưỡng Cosine Distance (`>0.3`). Kết quả là tạo ra một tệp đối tượng (candidates) ban đầu cực kì có chung nội dung/hình thái ảnh Q.
3. **Giai đoạn 2 (Re-ranking chấm điểm):** 
   - Với mỗi candidate thu được ở vòng 1, hệ thống gọi hàm chấm điểm lại `_compute_color_similarity(Q_colors, Candidate_colors)`.
   - Tính tổng hợp kết quả lai: `(50% điểm Vector DINOv2) + (50% điểm Màu sắc)`.
4. Trả về danh sách được sắp xếp tối ưu dựa trên điểm số lai.

---

## 3. Bản chất Toán học của thuật toán So sánh màu sắc

Hàm tính độ tương đồng `_compute_color_similarity()` được thực thi qua 3 phép toán tinh xảo:

### Bước 1: Chuyển độ lệch màu sang Không gian LAB
Hệ màu `RGB` trong máy tính không thể phản xạ được mức độ "nhìn chung dễ chịu" của mắt con người đối với các dải màu (ví dụ 2 mã số RGB rời rạc nhìn thấy giống nhau xì đúc).
- Mã nguồn chạy lệnh `cv2.cvtColor` biến các mã màu RGB của 2 bộ 3 màu này sang không gian màu **LAB (L*a*b)** chuẩn CIE.
- Khoảng cách vật lý giữa 2 tọa độ bất kì trong khung không gian LAB tỷ lệ thuận 1-1 với sự khác biệt cảm nhận của võng mạc con người. (Màu LAB giống nhau là mắt sẽ thấy giống nhau).

### Bước 2: Ma trận giá (Cost Matrix) & Thuật toán Hungary (Hungarian Algorithm)
Ta có 3 màu từ Ảnh A và 3 màu từ Ảnh B. Làm sao biết so sánh cặp màu nào qua ảnh kia?
- Xây dựng một **Ma trận 3x3** với 9 ô. Mỗi ô đong đếm khoảng cách **Euclidean Distance** theo chuẩn hệ LAB giữa bất kỳ 1 màu của A và 1 màu của B.
- Sử dụng **Thuật toán Hungary (Hungarian Algorithm)** để giải quyết bài toán Tối ưu hóa phân công (Assignment Problem) trên ma trận. Bằng thư viện `scipy...linear_sum_assignment`, thuật toán xoay chuyển tráo tổ hợp sao cho tổng lỗi sai lệch giữa 3 cặp ánh xạ chéo lúc chốt deal là NHỎ NHẤT thế giới.
- Kết quả: Ánh xạ chuẩn chỉ chéo nhất (Đỏ chéo Đỏ đun, Lam nhạt chéo Lam thẫm).

### Bước 3: Tính điểm số dùng trọng số Tỉ Lệ (Weighted Score)
Đối với mỗi cặp màu đã chốt deal:
- Tính **Điểm chênh lệch**: `1 - (Khoảng_cách_LAB / 375.0)`. Giới hạn max giới hạn độ rời rạc cực hạn khoảng ~375.
- Tính **Trọng số phân bổ ảnh**: Màu nền của 2 ảnh sẽ quan trọng gấp ti mỉ lần 1 chấm màu tô điểm trên áo họa tiết. Do đó quy đổi trọng số cặp màu bằng Trung bình cộng tỉ lệ diện tích: `Weight = (Ratio_A + Ratio_B) / 2`.
- Tính **Chung cuộc (Similarity%)**: Lấy tổng điểm các phần `[Điểm x Trọng Số]` đem chia cho tổng của toàn bộ các `[Trọng số]`. Tạo ra một mức độ tương tự `0.0 -> 100.0%` cực kỳ chuẩn với phản xạ thị giác sinh học người.
