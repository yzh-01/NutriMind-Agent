"""Database seed-data tests."""

from app.database.seed import DEFAULT_DETECTION_SCENE, init_seed
from app.entity.db_models import DetectionScene


def test_init_seed_creates_default_scene_idempotently(db):
    init_seed()
    init_seed()
    db.expire_all()

    scenes = (
        db.query(DetectionScene)
        .filter(DetectionScene.name == DEFAULT_DETECTION_SCENE["name"])
        .all()
    )
    assert len(scenes) == 1
    assert scenes[0].is_active is True
