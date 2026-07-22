"""头像服务 — 独立存储，每用户仅保留一张。"""

import os
from pathlib import Path
from typing import Optional

from app.config.settings import settings

AVATARS_DIR = settings.BASE_DIR / "data" / "avatars"


class AvatarService:
    """用户头像管理。"""

    def __init__(self) -> None:
        AVATARS_DIR.mkdir(parents=True, exist_ok=True)

    def _filepath(self, user_id: int) -> Path:
        """用户头像固定路径：{user_id}.png"""
        return AVATARS_DIR / f"{user_id}.png"

    def save(self, file_bytes: bytes, user_id: int) -> str:
        """保存头像（覆盖旧文件），返回 URL 路径。"""
        filepath = self._filepath(user_id)
        with open(filepath, "wb") as f:
            f.write(file_bytes)
        return f"/api/users/me/avatar/file/{user_id}.png"

    def delete(self, user_id: int) -> None:
        """删除用户头像。"""
        filepath = self._filepath(user_id)
        if filepath.exists():
            os.remove(filepath)

    def get_path(self, user_id: int) -> Optional[Path]:
        """获取头像文件路径，不存在返回 None。"""
        filepath = self._filepath(user_id)
        if filepath.exists():
            return filepath
        return None


# 全局单例
avatar_service = AvatarService()