"""Detection service validation tests."""

import asyncio

import pytest

from app.entity.db_models import DetectionScene, DetectionTask
from app.services.detection_service import (
    DetectionSceneNotFoundError,
    detection_service,
)


def test_invalid_scene_is_rejected_before_task_insert(db):
    with pytest.raises(DetectionSceneNotFoundError, match="999"):
        asyncio.run(
            detection_service.detect_from_path(
                db=db,
                scene_id=999,
                image_path="/tmp/not-used.jpg",
            )
        )

    assert db.query(DetectionTask).count() == 0


def test_inactive_scene_is_rejected_before_task_insert(db):
    scene = DetectionScene(
        name="inactive_scene",
        display_name="已停用场景",
        category="food",
        class_names=[],
        is_active=False,
    )
    db.add(scene)
    db.commit()

    with pytest.raises(DetectionSceneNotFoundError, match=str(scene.id)):
        asyncio.run(
            detection_service.detect_from_path(
                db=db,
                scene_id=scene.id,
                image_path="/tmp/not-used.jpg",
            )
        )

    assert db.query(DetectionTask).count() == 0
