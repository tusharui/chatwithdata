import os
import aiofiles
from fastapi import UploadFile
from app.config import get_settings

settings = get_settings()


class LocalStorage:
    def __init__(self):
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    async def save_file(self, file: UploadFile, dataset_id: str) -> str:
        dataset_dir = os.path.join(settings.UPLOAD_DIR, dataset_id)
        os.makedirs(dataset_dir, exist_ok=True)

        # Sanitize filename to prevent path traversal
        safe_name = os.path.basename(file.filename) if file.filename else f"{dataset_id}.upload"
        safe_name = safe_name.replace("..", "_").replace("/", "_").replace("\\", "_")
        file_path = os.path.join(dataset_dir, safe_name)

        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        return file_path

    def get_file_path(self, dataset_id: str, filename: str) -> str:
        safe_name = os.path.basename(filename)
        return os.path.join(settings.UPLOAD_DIR, dataset_id, safe_name)

    async def delete_file(self, file_path: str) -> bool:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False

    async def delete_dataset_dir(self, dataset_id: str) -> bool:
        import shutil
        dataset_dir = os.path.join(settings.UPLOAD_DIR, dataset_id)
        try:
            if os.path.exists(dataset_dir):
                shutil.rmtree(dataset_dir)
            return True
        except Exception:
            return False


storage = LocalStorage()
