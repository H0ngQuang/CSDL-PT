"""
Migration script: Add dominant_colors_json column to image_metadata table
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.config import get_settings
from sqlalchemy import create_engine, text

def migrate():
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # Check if column already exists
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'image_metadata' AND column_name = 'dominant_colors_json'
        """))
        
        if result.fetchone():
            print("✅ Column 'dominant_colors_json' already exists. Nothing to do.")
            return
        
        # Add the column
        conn.execute(text("ALTER TABLE image_metadata ADD COLUMN dominant_colors_json TEXT"))
        conn.commit()
        print("✅ Added column 'dominant_colors_json' to image_metadata table!")

if __name__ == "__main__":
    migrate()
