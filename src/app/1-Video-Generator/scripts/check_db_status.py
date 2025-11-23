import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.database import init_db, get_db
from src.models.db_models import DBVideo

init_db()
db = next(get_db())

video = db.query(DBVideo).order_by(DBVideo.id.desc()).first()
if video:
    print(f"Latest Video ID: {video.id}")
    print(f"Status: {video.status}")
    print(f"URL: {video.url}")
    print(f"Error: {video.error_message}")
else:
    print("No videos found.")
