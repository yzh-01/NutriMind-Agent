"""
Dashboard 看板 API 测试
测试总览、检测统计、训练统计、用户统计、状态分布等接口
"""
import pytest
from app.database.session import get_db
from app.services.user_service import user_service
from app.entity.db_models import DetectionScene, DetectionTask, TrainingTask, FoodNutrition
from main import app


class TestDashboardAPI:
    """看板 API 集成测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        """每个测试前覆盖数据库依赖"""
        def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        yield
        app.dependency_overrides.clear()

    def _get_token(self, client, db, username="dashuser", email="dash@example.com"):
        """辅助：注册并获取 Token"""
        user_service.register(db, username, email, "password123")
        resp = client.post("/api/auth/login", json={
            "username": username,
            "password": "password123",
        })
        return resp.json()["access_token"]

    def _auth_header(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    # ── 总览接口 ──────────────────────────────

    def test_overview_success(self, client, db):
        """GET /api/dashboard/overview 正常返回"""
        token = self._get_token(client, db)
        response = client.get("/api/dashboard/overview",
                              headers=self._auth_header(token))
        assert response.status_code == 200
        data = response.json()["data"]
        assert "total_users" in data
        assert "total_detection_tasks" in data
        assert "total_training_tasks" in data

    def test_overview_no_auth(self, client):
        """未登录访问 /overview 返回 401"""
        response = client.get("/api/dashboard/overview")
        assert response.status_code == 401

    def test_overview_counts_match_db(self, client, db):
        """总览数据与数据库记录一致"""
        # 插入测试数据
        user_service.register(db, "u1", "u1@example.com", "password123")
        user_service.register(db, "u2", "u2@example.com", "password123")

        scene = DetectionScene(
            name="test_sc", display_name="测试", category="food", class_names=["a"])
        db.add(scene)
        db.commit()
        db.refresh(scene)

        task = DetectionTask(scene_id=scene.id, status="completed",
                             total_objects=5, inference_time=0.12)
        db.add(task)
        db.commit()

        token = self._get_token(client, db, "viewer", "viewer@example.com")
        response = client.get("/api/dashboard/overview",
                              headers=self._auth_header(token))
        data = response.json()["data"]

        assert data["total_users"] >= 3  # u1, u2, viewer
        assert data["total_detection_tasks"] >= 1
        assert data["total_detection_scenes"] >= 1

    # ── 检测统计接口 ──────────────────────────

    def test_detection_stats_empty(self, client, db):
        """空数据库时检测统计全为 0"""
        token = self._get_token(client, db)
        response = client.get("/api/dashboard/detection",
                              headers=self._auth_header(token))
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] == 0
        assert data["completed"] == 0
        assert data["avg_inference_time"] is None

    def test_detection_stats_with_data(self, client, db):
        """有数据时检测统计正确"""
        scene = DetectionScene(
            name="det_sc", display_name="检测", category="food", class_names=["a"])
        db.add(scene)
        db.commit()
        db.refresh(scene)

        db.add_all([
            DetectionTask(scene_id=scene.id, status="completed",
                          total_objects=3, inference_time=0.5),
            DetectionTask(scene_id=scene.id, status="completed",
                          total_objects=2, inference_time=0.3),
            DetectionTask(scene_id=scene.id, status="failed"),
            DetectionTask(scene_id=scene.id, status="pending"),
        ])
        db.commit()

        token = self._get_token(client, db)
        response = client.get("/api/dashboard/detection",
                              headers=self._auth_header(token))
        data = response.json()["data"]

        assert data["total"] == 4
        assert data["completed"] == 2
        assert data["failed"] == 1
        assert data["pending"] == 1
        assert data["total_objects_detected"] == 5
        assert data["avg_inference_time"] == pytest.approx(0.4, abs=0.01)

    # ── 训练统计接口 ──────────────────────────

    def test_training_stats_empty(self, client, db):
        """空数据库时训练统计全为 0"""
        token = self._get_token(client, db)
        response = client.get("/api/dashboard/training",
                              headers=self._auth_header(token))
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] == 0

    def test_training_stats_with_data(self, client, db):
        """有数据时训练统计正确"""
        db.add_all([
            TrainingTask(model_name="yolo26n",
                         data_yaml="/data/a.yaml", status="completed"),
            TrainingTask(model_name="yolo26n",
                         data_yaml="/data/b.yaml", status="running"),
            TrainingTask(model_name="yolo26n",
                         data_yaml="/data/c.yaml", status="paused"),
            TrainingTask(model_name="yolo26n",
                         data_yaml="/data/d.yaml", status="failed"),
        ])
        db.commit()

        token = self._get_token(client, db)
        response = client.get("/api/dashboard/training",
                              headers=self._auth_header(token))
        data = response.json()["data"]

        assert data["total"] == 4
        assert data["completed"] == 1
        assert data["running"] == 1
        assert data["paused"] == 1
        assert data["failed"] == 1

    # ── 用户统计接口 ──────────────────────────

    def test_user_stats(self, client, db):
        """用户统计数据正确"""
        user_service.register(db, "user_a", "a@example.com", "password123")
        user_service.register(db, "user_b", "b@example.com", "password123")

        token = self._get_token(client, db, "user_c", "c@example.com")
        response = client.get("/api/dashboard/users",
                              headers=self._auth_header(token))
        data = response.json()["data"]

        assert data["total"] >= 3
        assert data["active"] >= 3
        assert data["new_today"] >= 1  # 今天至少注册了 user_c

    # ── 完整看板聚合接口 ──────────────────────

    def test_full_stats(self, client, db):
        """GET /api/dashboard/stats 返回完整聚合数据"""
        token = self._get_token(client, db)
        response = client.get("/api/dashboard/stats",
                              headers=self._auth_header(token))
        assert response.status_code == 200
        data = response.json()["data"]

        assert "overview" in data
        assert "detection" in data
        assert "training" in data
        assert "users" in data
        assert isinstance(data["overview"]["total_users"], int)

    # ── 状态分布接口 ──────────────────────────

    def test_detection_status_distribution(self, client, db):
        """检测任务状态分布正确"""
        scene = DetectionScene(
            name="dist_sc", display_name="分布", category="food", class_names=["a"])
        db.add(scene)
        db.commit()
        db.refresh(scene)

        db.add_all([
            DetectionTask(scene_id=scene.id, status="completed"),
            DetectionTask(scene_id=scene.id, status="completed"),
            DetectionTask(scene_id=scene.id, status="pending"),
        ])
        db.commit()

        token = self._get_token(client, db)
        response = client.get(
            "/api/dashboard/detection/status-distribution",
            headers=self._auth_header(token),
        )
        assert response.status_code == 200
        data = response.json()["data"]

        status_map = {item["status"]: item["count"] for item in data}
        assert status_map.get("completed") == 2
        assert status_map.get("pending") == 1

    def test_training_status_distribution(self, client, db):
        """训练任务状态分布正确"""
        db.add_all([
            TrainingTask(model_name="yolo26n",
                         data_yaml="/data/a.yaml", status="running"),
            TrainingTask(model_name="yolo26n",
                         data_yaml="/data/b.yaml", status="running"),
            TrainingTask(model_name="yolo26n",
                         data_yaml="/data/c.yaml", status="completed"),
        ])
        db.commit()

        token = self._get_token(client, db)
        response = client.get(
            "/api/dashboard/training/status-distribution",
            headers=self._auth_header(token),
        )
        data = response.json()["data"]

        status_map = {item["status"]: item["count"] for item in data}
        assert status_map.get("running") == 2
        assert status_map.get("completed") == 1
