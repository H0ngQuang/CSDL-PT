import sys
import os
import glob
from pathlib import Path
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.services.database_service import DatabaseService
from api.services.image_processor import ImageProcessor
from api.config import get_settings
from sqlalchemy.orm import Session
from sqlalchemy import text

def batch_import_existing_images():
    settings = get_settings()
    db_service = DatabaseService()
    image_processor = ImageProcessor()
    
    uploads_dir = Path(settings.uploads_dir)
    image_files = list(uploads_dir.glob("*.jpg")) + list(uploads_dir.glob("*.jpeg")) + list(uploads_dir.glob("*.png"))
    
    if not image_files:
        print("No images found in", uploads_dir)
        return
        
    print(f"Found {len(image_files)} images in {uploads_dir}. Starting import...")
    
    session = db_service.get_session()
    
    # First clear existing records just in case
    session.execute(text("TRUNCATE TABLE image_metadata RESTART IDENTITY"))
    session.commit()
    
    success_count = 0
    error_count = 0
    
    try:
        for file_path in image_files:
            try:
                print(f"Processing {file_path.name}...")
                features = image_processor.extract_features(file_path)
                
                # Check if dinov2_vector was successfully extracted
                if 'dinov2_vector' not in features or features['dinov2_vector'] is None:
                    print(f"Warning: DINOv2 vector extraction failed for {file_path.name}")
                    
                # The file is already in uploads with a UUID name, so we use it as unique_filename
                # The original name is lost, we'll just use the UUID name
                db_service.create_image_metadata(
                    db=session,
                    file_name=file_path.name, # Use current name as original name
                    unique_filename=file_path.name,
                    features=features
                )
                success_count += 1
            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")
                error_count += 1
                
        print(f"\nImport completed: {success_count} succeeded, {error_count} failed.")
        
        # Verify
        count = session.execute(text('SELECT COUNT(*) FROM image_metadata')).scalar()
        print(f"Total entries in DB after import: {count}")
    finally:
        session.close()

if __name__ == "__main__":
    batch_import_existing_images()
