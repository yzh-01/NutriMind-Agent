"""摄像头服务 — 图片保存、查询、删除，按用户隔离。"""

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

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    @staticmethod
    def _make_filename(user_id: int) -> str:
        """生成带用户归属的文件名：{user_id}_{uuid}.png"""
        return f"{user_id}_{uuid.uuid4().hex}.png"

    @staticmethod
    def _parse_user_id(filename: str) -> Optional[int]:
        """从文件名提取 user_id，格式不符返回 None。"""
        try:
            return int(filename.split("_", 1)[0])
        except (ValueError, IndexError):
            return None

    # ------------------------------------------------------------------
    # 公开方法
    # ------------------------------------------------------------------

    def save_image(self, file_bytes: bytes, original_filename: str, user_id: int) -> dict:
        """保存上传的图片（不暴露服务器路径）。

        Returns:
            dict: {id, original_name, size, user_id, created_at}
        """
        filename = self._make_filename(user_id)
        filepath = CAPTURES_DIR / filename

        with open(filepath, "wb") as f:
            f.write(file_bytes)

        return {
            "id": filename,
            "original_name": original_filename,
            "size": len(file_bytes),
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
        }

    def list_images(self, user_id: int, page: int = 1, page_size: int = 20) -> dict:
        """列出当前用户的图片（按时间倒序）。

        Returns:
            dict: {items, total, page, page_size}
        """
        prefix = f"{user_id}_"
        all_images = []
        for f in sorted(CAPTURES_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if not f.is_file():
                continue
            if not f.name.startswith(prefix):
                continue
            if f.suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}:
                continue
            stat = f.stat()
            all_images.append({
                "id": f.name,
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })

        total = len(all_images)
        start = (page - 1) * page_size
        items = all_images[start:start + page_size]

        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def delete_image(self, image_id: str, user_id: int) -> bool:
        """删除指定图片（验证所有权）。

        Returns:
            bool: 是否成功删除
        """
        if self._parse_user_id(image_id) != user_id:
            return False
        filepath = CAPTURES_DIR / image_id
        if filepath.exists() and filepath.is_file():
            os.remove(filepath)
            return True
        return False

    def get_image_path(self, image_id: str, user_id: int) -> Optional[Path]:
        """获取图片文件路径（验证所有权）。"""
        if self._parse_user_id(image_id) != user_id:
            return None
        filepath = CAPTURES_DIR / image_id
        if filepath.exists():
            return filepath
        return None


# 全局单例
camera_service = CameraService()