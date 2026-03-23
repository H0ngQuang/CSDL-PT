"""
Database Service
Manages database connections and operations
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Optional
import logging

from ..models.database import Base, ImageMetadata
from ..config import get_settings

logger = logging.getLogger(__name__)


class DatabaseService:
    """Database connection and operations manager"""
    
    def __init__(self):
        """Initialize database service"""
        self.settings = get_settings()
        self.engine = create_engine(
            self.settings.database_url, 
            echo=False
        )
        self.SessionLocal = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=self.engine
        )
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Create tables if they don't exist"""
        try:
            # First, ensure the vector extension exists
            with self.engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
    
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables ensured")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise
    
    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()
    
    def create_image_metadata(
        self,
        db: Session,
        file_name: str,
        unique_filename: str,
        features: dict
    ) -> ImageMetadata:

        try:
            image_record = ImageMetadata(
                file_name=file_name,
                unique_filename=unique_filename,
                width=features.get('width'),
                height=features.get('height'),
                brightness=features.get('brightness'),
                contrast=features.get('contrast'),
                saturation=features.get('saturation'),
                edge_density=features.get('edge_density'),

                features_json=features.get('features_json'),
                dinov2_vector=features.get('dinov2_vector')
            )
            
            db.add(image_record)
            db.commit()
            db.refresh(image_record)
            
            logger.info(f"Created image metadata: ID {image_record.id}")
            return image_record
            
        except Exception as e:
            logger.error(f"Error creating image metadata: {e}")
            db.rollback()
            raise
    
    def update_image_metadata(
        self,
        db: Session,
        image_id: int,
        features: dict
    ) -> Optional[ImageMetadata]:
        """
        Update image metadata with new features
        """
        try:
            image = self.get_image_by_id(db, image_id)
            if not image:
                return None
                
            # Update fields
            image.width = features.get('width')
            image.height = features.get('height')
            image.brightness = features.get('brightness')
            image.contrast = features.get('contrast')
            image.saturation = features.get('saturation')
            image.edge_density = features.get('edge_density')

            image.features_json = features.get('features_json')
            
            if 'dinov2_vector' in features:
                image.dinov2_vector = features.get('dinov2_vector')
            
            db.commit()
            db.refresh(image)
            
            logger.info(f"Updated image metadata: ID {image.id}")
            return image
            
        except Exception as e:
            logger.error(f"Error updating image metadata: {e}")
            db.rollback()
            raise
    
    def get_images(
        self,
        db: Session,
        limit: int = 100,
        offset: int = 0
    ) -> List[ImageMetadata]:

        try:
            images = db.query(ImageMetadata)\
                .order_by(ImageMetadata.created_at.desc())\
                .limit(limit)\
                .offset(offset)\
                .all()
            
            return images
            
        except Exception as e:
            logger.error(f"Error fetching images: {e}")
            raise
    
    def search_images_by_vector(
        self,
        db: Session,
        query_vector: list[float],
        threshold: float = 0.3,
        limit: int = 100
    ) -> List[tuple[ImageMetadata, float]]:
        """
        Search for similar images using pgvector.
        Returns tuples of (ImageMetadata, vector_similarity)
        where vector_similarity = 1 - cosine_distance.
        """
        try:
            # We want similarity > threshold.
            # Cosine distance in pgvector is operator <=>. Similarity = 1 - distance
            # So distance < (1 - threshold)
            
            distance = ImageMetadata.dinov2_vector.cosine_distance(query_vector)
            similarity_expr = 1.0 - distance
            
            results = db.query(ImageMetadata, similarity_expr.label('vector_sim'))\
                .filter(similarity_expr > threshold)\
                .order_by(distance)\
                .limit(limit)\
                .all()
            
            return results
            
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            raise
    
    def get_image_by_id(self, db: Session, image_id: int) -> Optional[ImageMetadata]:
        """
        Get image by ID
        
        Args:
            db: Database session
            image_id: Image ID
            
        Returns:
            ImageMetadata or None
        """
        try:
            return db.query(ImageMetadata)\
                .filter(ImageMetadata.id == image_id)\
                .first()
        except Exception as e:
            logger.error(f"Error fetching image {image_id}: {e}")
            raise
