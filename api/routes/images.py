"""
Image Routes
Image upload and retrieval endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import logging
import json

from ..models.schemas import ImageResponse, SearchResponse
from ..services import DatabaseService, ImageProcessor
from ..utils.dependencies import get_db, get_database_service, get_image_processor
from ..config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/images", tags=["images"])


def _parse_features_json(features_json):
    """Helper to safely parse features_json from string or dict"""
    if features_json is None:
        return None
    if isinstance(features_json, dict):
        return features_json
    if isinstance(features_json, str):
        return json.loads(features_json)
    return None




@router.post("/upload", response_model=List[ImageResponse])
async def upload_images(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    db_service: DatabaseService = Depends(get_database_service),
    image_processor: ImageProcessor = Depends(get_image_processor)
):

    results = []
    settings = get_settings()
    
    try:
        for file in files:
            # Validate file type
            if not image_processor.validate_image(file.content_type):
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} is not an image"
                )
            
            # Save file
            content = await file.read()
            file_path, unique_filename = image_processor.save_upload(
                content,
                file.filename
            )
            print(f"✅ file_path: {file_path}")
            print(f"✅ unique_filename: {unique_filename}")
            # Extract features
            features = image_processor.extract_features(file_path)
            print(f"✅ features: {features}")
            logger.info(f"Extracted features for {file.filename}")
            
            # Save to database
            image_record = db_service.create_image_metadata(
                db=db,
                file_name=file.filename,
                unique_filename=unique_filename,
                features=features
            )
            print(f"✅ image_record: {image_record}")
            # Build response
            result = ImageResponse(
                id=image_record.id,
                file_name=image_record.file_name,
                url=f"/static/uploads/{unique_filename}",
                width=image_record.width,
                height=image_record.height,
                brightness=image_record.brightness,
                contrast=image_record.contrast,
                saturation=image_record.saturation,
                edge_density=image_record.edge_density,
                features_json=_parse_features_json(image_record.features_json),
                created_at=image_record.created_at
            )
            
            results.append(result)
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading images: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[ImageResponse])
async def get_images(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    db_service: DatabaseService = Depends(get_database_service)
):

    try:
        images = db_service.get_images(db, limit=limit, offset=offset)
        
        # Build responses
        results = []
        for image in images:
            result = ImageResponse(
                id=image.id,
                file_name=image.file_name,
                url=f"/static/uploads/{image.unique_filename}",
                width=image.width,
                height=image.height,
                brightness=image.brightness,
                contrast=image.contrast,
                saturation=image.saturation,
                edge_density=image.edge_density,
                features_json=_parse_features_json(image.features_json),
                created_at=image.created_at
            )
            results.append(result)
        
        return results
        
    except Exception as e:
        logger.error(f"Error fetching images: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recompute", response_model=List[ImageResponse])
async def recompute_all_features(
    db: Session = Depends(get_db),
    db_service: DatabaseService = Depends(get_database_service),
    image_processor: ImageProcessor = Depends(get_image_processor)
):
    """
    Recompute features for ALL images
    """
    settings = get_settings()
    updated_images = []
    
    try:
        # 1. Get ALL images (simulate unlimited by setting high limit)
        # In production, this should be a background task or paginated
        images = db_service.get_images(db, limit=10000)
        
        for image in images:
            try:
                # 2. Get file path
                file_path = settings.uploads_dir / image.unique_filename
                
                if not file_path.exists():
                    logger.warning(f"File not found for image {image.id}: {file_path}")
                    continue
                    
                # 3. Re-extract features
                features = image_processor.extract_features(file_path)
                
                # 4. Update database
                updated_image = db_service.update_image_metadata(db, image.id, features)
                
                if updated_image:
                    updated_images.append(updated_image)
                    
            except Exception as e:
                logger.error(f"Error recomputing image {image.id}: {e}")
                # Continue to next image even if one fails
                continue

        # 5. Return updated list
        return [
            ImageResponse(
                id=img.id,
                file_name=img.file_name,
                url=f"/static/uploads/{img.unique_filename}",
                width=img.width,
                height=img.height,
                brightness=img.brightness,
                contrast=img.contrast,
                saturation=img.saturation,
                edge_density=img.edge_density,
                features_json=_parse_features_json(img.features_json),
                created_at=img.created_at
            ) for img in updated_images
        ]

    except Exception as e:
        logger.error(f"Error in global recompute: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SearchResponse)
async def search_similar_images(
    file: UploadFile = File(...),
    limit: int = 5,
    db: Session = Depends(get_db),
    db_service: DatabaseService = Depends(get_database_service),
    image_processor: ImageProcessor = Depends(get_image_processor)
):
    """
    Search for similar images
    """
    try:
        # 1. Validate and Read Query Image
        if not image_processor.validate_image(file.content_type):
            raise HTTPException(status_code=400, detail="Invalid image file")
        
        content = await file.read()
        
        # 2. Save temporarily to extract features (or process in-memory if refactored, 
        # but existing extract_features takes a path)
        # We'll save it as a temp file
        file_path, unique_filename = image_processor.save_upload(content, file.filename)
        
        try:
            # 3. Extract Features
            query_features = image_processor.extract_features(file_path)
            
            # Stage 1: Search using pgvector DINOv2 embeddings (100% vector similarity)
            query_vector = query_features.get('dinov2_vector')
            if not query_vector:
                raise ValueError("Failed to extract DINOv2 vector from query image")
                
            filtered_candidates = db_service.search_images_by_vector(
                db=db, 
                query_vector=query_vector, 
                threshold=0.3,
                limit=limit
            )
            
            # Format Response
            response = []
            for img, vector_sim in filtered_candidates:
                similarity_percent = float(vector_sim) * 100.0
                
                response.append(ImageResponse(
                    id=img.id,
                    file_name=img.file_name,
                    url=f"/static/uploads/{img.unique_filename}",
                    width=img.width,
                    height=img.height,
                    brightness=img.brightness,
                    contrast=img.contrast,
                    saturation=img.saturation,
                    edge_density=img.edge_density,
                    features_json=_parse_features_json(img.features_json),
                    similarity=similarity_percent,
                    created_at=img.created_at
                ))
            if 'features_json' in query_features:
                query_features['features_json'] = _parse_features_json(query_features['features_json'])
                
            return SearchResponse(
                query_image=query_features,
                results=response
            )

        finally:
            # Cleanup temp file? 
            # For this app, maybe we want to keep the uploaded search image?
            # The prompt doesn't say. Let's keep it in uploads for now as it aids debugging/history if we wanted.
            pass

    except Exception as e:
        logger.error(f"Error searching images: {e}")
        raise HTTPException(status_code=500, detail=str(e))

