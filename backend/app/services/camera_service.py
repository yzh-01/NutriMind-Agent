"""摄像头服务 — 图片保存、查询、删除。"""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config.settings import settings

CAPTURES_DIR = settings.BASE_DIR / "data" / "captures"


class CameraService:
    """摄像头图片管理服务。"""

    def __init__(self) -> None:
        CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

    def save_image(self, file_bytes: bytes, original_filename: str, user_id: int) -> dict:
        """保存上传的图片到本地。

        Returns:
            dict: {id, original_name, filename, path, size, user_id, created_at}
        """
        ext = Path(original_filename).suffix.lower() or ".png"
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = CAPTURES_DIR / filename

        with open(filepath, "wb") as f:
            f.write(file_bytes)

        return {
            "id": filename,
            "original_name": original_filename,
            "filename": filename,
            "path": str(filepath),
            "size": len(file_bytes),
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
        }

    def list_images(self, user_id: Optional[int] = None, page: int = 1, page_size: int = 20) -> dict:
        """列出已保存的图片（按时间倒序）。

        Returns:
            dict: {items, total, page, page_size}
        """
        files = sorted(
            CAPTURES_DIR.iterdir(),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        all_images = []
        for f in files:
            if f.is_file() and f.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}:
                stat = f.stat()
                all_images.append({
                    "id": f.name,
                    "filename": f.name,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })

        # 分页
        total = len(all_images)
        start = (page - 1) * page_size
        end = start + page_size
        items = all_images[start:end]

        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def delete_image(self, image_id: str) -> bool:
        """删除指定图片。

        Returns:
            bool: 是否成功删除
        """
        filepath = CAPTURES_DIR / image_id
        if filepath.exists() and filepath.is_file():
            os.remove(filepath)
            return True
        return False

    def get_image_path(self, image_id: str) -> Optional[Path]:
        """获取图片文件路径。"""
        filepath = CAPTURES_DIR / image_id
        if filepath.exists():
            return filepath
        return None


# 全局单例
camera_service = CameraService()