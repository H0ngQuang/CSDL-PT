"""
Image Processor Service
Handles image processing and feature extraction
"""

import cv2
import numpy as np
from sklearn.cluster import KMeans
from scipy.optimize import linear_sum_assignment
from pathlib import Path
import uuid
import logging
import json
from typing import Dict
from PIL import Image
import torch
from transformers import AutoImageProcessor, AutoModel

from ..config import get_settings

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Image processing and feature extraction service"""
    
    def __init__(self):
        """Initialize image processor"""
        self.settings = get_settings()
        
        # Load DINOv2 model and processor
        logger.info("Loading DINOv2 model for feature extraction...")
        # Using the small version which provides 384d vectors and is fast
        self.dino_processor = AutoImageProcessor.from_pretrained('facebook/dinov2-small')
        self.dino_model = AutoModel.from_pretrained('facebook/dinov2-small')
        
        # Use GPU if available
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.dino_model.to(self.device)
        self.dino_model.eval()
        logger.info(f"DINOv2 loaded successfully on {self.device}")
    
    def save_upload(self, content: bytes, original_filename: str) -> tuple[Path, str]:

        try:
            # Generate unique filename
            file_ext = Path(original_filename).suffix
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = self.settings.uploads_dir / unique_filename
            
            # Save file
            with open(file_path, "wb") as f:
                f.write(content)
            
            logger.info(f"Saved file: {file_path}")
            return file_path, unique_filename
            
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            raise
    
    def extract_features(self, image_path: Path) -> Dict:

        try:
            with open(image_path, 'rb') as f:
                file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            print(f"✅ img: {img}")
            if img is None:
                raise ValueError(f"Failed to read image: {image_path}")
            
            height, width = img.shape[:2]
            
            # Convert to grayscale for analysis
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Brightness (mean of grayscale)
            brightness = float(np.mean(gray) / 255.0)
            
            # Contrast (std of grayscale)
            contrast = float(np.std(gray) / 255.0)
            
            # Saturation (mean of S channel in HSV)
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            saturation = float(np.mean(hsv[:, :, 1]) / 255.0)
            
            # Edge density (Canny edges)
            edges = cv2.Canny(gray, 100, 200)
            edge_density = float(np.sum(edges > 0) / (height * width))
            
            # Dominant color (k-means on downsampled pixels)
            dominant_hex = self._extract_dominant_color(img)
            
            # Extract top 3 dominant colors with ratios
            dominant_colors = self._extract_top_colors(img, k=3)
            
            # Histogram for features_json
            features_json = self._extract_histogram_features(img, edge_density, contrast)
            
            # --- DINOv2 Feature Extraction ---
            # Convert OpenCV BGR image to PIL RGB image for Transformers
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_img)
            
            # Prepare inputs and run model
            inputs = self.dino_processor(images=pil_img, return_tensors="pt").to(self.device)
            with torch.no_grad():
                outputs = self.dino_model(**inputs)
            
            # We take the [CLS] token representation (the first token) as the global image feature
            hidden_states = outputs.last_hidden_state
            vector = hidden_states[0, 0, :].cpu().numpy()
            
            # Normalize vector to unit length (L2 norm = 1) for cosine similarity
            vector = vector / np.linalg.norm(vector)
            
            return {
                'width': width,
                'height': height,
                'brightness': brightness,
                'contrast': contrast,
                'saturation': saturation,
                'edge_density': edge_density,
                'dominant_color_hex': dominant_hex,
                'dominant_colors': dominant_colors,
                'dominant_colors_json': json.dumps(dominant_colors),
                'features_json': json.dumps(features_json),
                'dinov2_vector': vector.tolist()
            }
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            raise
    
    def _extract_dominant_color(self, img: np.ndarray) -> str:
        """
        Extract dominant color using K-means clustering
        
        Args:
            img: OpenCV image (BGR format)
            
        Returns:
            Hex color string
        """
        # Downsample for performance
        small_img = cv2.resize(img, (100, 100))
        pixels = small_img.reshape(-1, 3).astype(np.float32)
        
        # K-means clustering
        kmeans = KMeans(n_clusters=1, n_init=1, random_state=42)
        kmeans.fit(pixels)
        dominant_bgr = kmeans.cluster_centers_[0]
        
        # Convert BGR to RGB
        dominant_rgb = dominant_bgr[::-1]
        
        # Convert to hex
        dominant_hex = '#{:02x}{:02x}{:02x}'.format(
            int(dominant_rgb[0]),
            int(dominant_rgb[1]),
            int(dominant_rgb[2])
        )
        
        return dominant_hex
    
    def _extract_top_colors(self, img: np.ndarray, k: int = 3) -> list:
        """
        Extract top k dominant colors with their ratios using K-Means.
        
        Args:
            img: OpenCV image (BGR format)
            k: Number of dominant colors to extract
            
        Returns:
            List of dicts sorted by ratio descending:
            [{"hex": "#2a5f8e", "rgb": [42, 95, 142], "ratio": 0.52}, ...]
        """
        # Downsample for performance
        small_img = cv2.resize(img, (100, 100))
        pixels = small_img.reshape(-1, 3).astype(np.float32)
        
        # K-Means clustering with k clusters
        kmeans = KMeans(n_clusters=k, n_init=3, random_state=42)
        labels = kmeans.fit_predict(pixels)
        
        # Count pixels per cluster to get ratios
        total_pixels = len(labels)
        colors = []
        for i in range(k):
            count = int(np.sum(labels == i))
            ratio = round(count / total_pixels, 4)
            
            # BGR -> RGB
            bgr = kmeans.cluster_centers_[i]
            rgb = [int(bgr[2]), int(bgr[1]), int(bgr[0])]
            hex_color = '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])
            
            colors.append({
                "hex": hex_color,
                "rgb": rgb,
                "ratio": ratio
            })
        
        # Sort by ratio descending (most dominant first)
        colors.sort(key=lambda c: c["ratio"], reverse=True)
        return colors
    
    def _compute_color_similarity(self, colors1: list, colors2: list) -> float:
        """
        Compute color similarity between two sets of dominant colors.
        
        Uses Hungarian algorithm to optimally map colors from image 1 to image 2,
        then computes weighted similarity based on LAB color distance.
        
        Args:
            colors1: List of dominant colors from image 1 [{hex, rgb, ratio}, ...]
            colors2: List of dominant colors from image 2 [{hex, rgb, ratio}, ...]
            
        Returns:
            Similarity score between 0.0 and 100.0
        """
        if not colors1 or not colors2:
            return 0.0
        
        n1 = len(colors1)
        n2 = len(colors2)
        
        # Convert RGB colors to LAB for perceptually uniform distance
        lab_colors1 = []
        lab_colors2 = []
        
        for c in colors1:
            rgb = np.array([[c["rgb"]]], dtype=np.uint8)
            lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
            lab_colors1.append(lab[0, 0].astype(np.float64))
        
        for c in colors2:
            rgb = np.array([[c["rgb"]]], dtype=np.uint8)
            lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
            lab_colors2.append(lab[0, 0].astype(np.float64))
        
        # Build cost matrix (Euclidean distance in LAB space)
        cost_matrix = np.zeros((n1, n2))
        for i in range(n1):
            for j in range(n2):
                cost_matrix[i, j] = np.linalg.norm(lab_colors1[i] - lab_colors2[j])
        
        # Hungarian algorithm for optimal matching
        row_idx, col_idx = linear_sum_assignment(cost_matrix)
        
        # Max possible LAB distance (~375 for extreme colors)
        MAX_LAB_DISTANCE = 375.0
        
        # Compute weighted similarity for each matched pair
        weighted_sim_sum = 0.0
        weight_sum = 0.0
        
        for r, c in zip(row_idx, col_idx):
            distance = cost_matrix[r, c]
            color_sim = 1.0 - (distance / MAX_LAB_DISTANCE)
            color_sim = max(color_sim, 0.0)
            
            # Weight = average ratio of the two matched colors
            weight = (colors1[r]["ratio"] + colors2[c]["ratio"]) / 2.0
            
            weighted_sim_sum += color_sim * weight
            weight_sum += weight
        
        if weight_sum == 0:
            return 0.0
        
        similarity = (weighted_sim_sum / weight_sum) * 100.0
        return min(max(similarity, 0.0), 100.0)
    
    def _extract_histogram_features(
        self,
        img: np.ndarray,
        edge_density: float,
        contrast: float
    ) -> Dict:
        """
        Extract histogram and additional features
        
        Args:
            img: OpenCV image (BGR format)
            edge_density: Pre-computed edge density
            contrast: Pre-computed contrast
            
        Returns:
            Dictionary of histogram features
        """
        height, width = img.shape[:2]
        total_pixels = height * width
        
        hist_b = cv2.calcHist([img], [0], None, [16], [0, 256])
        hist_g = cv2.calcHist([img], [1], None, [16], [0, 256])
        hist_r = cv2.calcHist([img], [2], None, [16], [0, 256])
        
        # Normalize to ratios (0.0 to 1.0) and round to 4 decimal places
        hist_b_ratio = [round(float(val[0]) / total_pixels, 4) for val in hist_b]
        hist_g_ratio = [round(float(val[0]) / total_pixels, 4) for val in hist_g]
        hist_r_ratio = [round(float(val[0]) / total_pixels, 4) for val in hist_r]
        
        return {
            "histogram": {
                "blue": hist_b_ratio,
                "green": hist_g_ratio,
                "red": hist_r_ratio
            },
            "texture_score": float(edge_density),
            "quality_score": float(contrast)
        }
    
    def validate_image(self, content_type: str) -> bool:
        """
        Validate if file is an image
        
        Args:
            content_type: MIME content type
            
        Returns:
            True if valid image
        """
        return content_type.startswith('image/')

    def compute_similarity(self, features1: Dict, features2: Dict) -> float:
        """
        Compute similarity between two images based on their dominant colors.
        Uses Hungarian matching on top 3 colors in LAB color space,
        weighted by each color's ratio.
        
        Args:
            features1: Features dictionary of first image
            features2: Features dictionary of second image
            
        Returns:
            Similarity score between 0.0 and 100.0
        """
        try:
            # Get dominant colors from features
            colors1 = features1.get('dominant_colors')
            colors2 = features2.get('dominant_colors')

            # Parse from JSON string if needed
            if isinstance(colors1, str):
                colors1 = json.loads(colors1)
            if isinstance(colors2, str):
                colors2 = json.loads(colors2)

            if not colors1 or not colors2:
                return 0.0

            return self._compute_color_similarity(colors1, colors2)

        except Exception as e:
            logger.error(f"Error computing similarity: {e}")
            return 0.0
