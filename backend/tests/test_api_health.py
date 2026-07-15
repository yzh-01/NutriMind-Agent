"""
健康检查 API 测试
"""
import pytest
from main import app


class TestHealthAPI:
    """健康检查 API 测试"""

    def test_health_check(self, client):
        """GET /api/health 健康检查返回 200"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "message" in data

    def test_health_check_response_format(self, client):
        """健康检查响应包含必要字段"""
        response = client.get("/api/health")
        data = response.json()
        assert "status" in data
        assert "message" in data
