"""
Image Processor Service
Handles image processing and feature extraction
"""

import cv2
import numpy as np

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
                'features_json': json.dumps(features_json),
                'dinov2_vector': vector.tolist()
            }
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            raise
    

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

    @staticmethod
    def compute_histogram_similarity(hist1: dict, hist2: dict) -> float:
        """
        Compute histogram intersection similarity between two histogram feature dicts.
        Each dict has keys 'red', 'green', 'blue' with lists of bin ratios.
        Returns a value in [0, 1] where 1 = identical histograms.
        """
        total_sim = 0.0
        channels = ['red', 'green', 'blue']
        
        for channel in channels:
            h1 = hist1.get(channel, [])
            h2 = hist2.get(channel, [])
            if h1 and h2 and len(h1) == len(h2):
                # Histogram intersection: sum of min values
                intersection = sum(min(a, b) for a, b in zip(h1, h2))
                total_sim += intersection
        
        return total_sim / len(channels) if channels else 0.0

    @staticmethod
    def compute_feature_similarity(query_features: dict, candidate_features: dict) -> float:
        """
        Compute similarity based on image properties (brightness, contrast, saturation, edge_density).
        Returns a value in [0, 1] where 1 = identical features.
        """
        import math
        feature_keys = ['brightness', 'contrast', 'saturation', 'edge_density']
        
        sum_sq_diff = 0.0
        for key in feature_keys:
            q_val = float(query_features.get(key, 0.0) or 0.0)
            c_val = float(candidate_features.get(key, 0.0) or 0.0)
            sum_sq_diff += (q_val - c_val) ** 2
        
        # Max possible distance = sqrt(4 * 1^2) = 2.0
        max_distance = math.sqrt(len(feature_keys))
        distance = math.sqrt(sum_sq_diff)
        
        return 1.0 - (distance / max_distance)


