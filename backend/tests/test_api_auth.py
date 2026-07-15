"""
认证 API 端点测试：注册、登录、获取当前用户
"""
import pytest
from app.database.session import get_db
from main import app
from app.services.user_service import user_service


class TestAuthAPI:
    """认证 API 集成测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        """每个测试前重置数据库并覆盖依赖"""
        def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        yield
        app.dependency_overrides.clear()

    # ── 注册接口测试 ──────────────────────────────

    def test_register_success(self, client):
        """POST /api/auth/register 正常注册"""
        response = client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "password123",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"
        assert "id" in data
        assert data["is_active"] is True
        assert data["is_superuser"] is False

    def test_register_duplicate_username(self, client, db):
        """重复用户名注册返回 400"""
        user_service.register(db, "dupuser", "a@example.com", "password123")
        response = client.post("/api/auth/register", json={
            "username": "dupuser",
            "email": "b@example.com",
            "password": "password123",
        })
        assert response.status_code == 400
        assert "用户名已存在" in response.json()["detail"]

    def test_register_duplicate_email(self, client, db):
        """重复邮箱注册返回 400"""
        user_service.register(db, "user1", "dup@example.com", "password123")
        response = client.post("/api/auth/register", json={
            "username": "user2",
            "email": "dup@example.com",
            "password": "password123",
        })
        assert response.status_code == 400

    def test_register_short_username(self, client):
        """用户名过短返回 422"""
        response = client.post("/api/auth/register", json={
            "username": "ab",
            "email": "short@example.com",
            "password": "password123",
        })
        assert response.status_code == 422

    def test_register_short_password(self, client):
        """密码过短返回 422"""
        response = client.post("/api/auth/register", json={
            "username": "validuser",
            "email": "valid@example.com",
            "password": "12345",
        })
        assert response.status_code == 422

    def test_register_missing_fields(self, client):
        """缺少必填字段返回 422"""
        response = client.post("/api/auth/register", json={
            "username": "incomplete",
        })
        assert response.status_code == 422

    # ── 登录接口测试 ──────────────────────────────

    def test_login_success(self, client, db):
        """POST /api/auth/login 正常登录"""
        user_service.register(
            db, "loginuser", "login@example.com", "password123")
        response = client.post("/api/auth/login", json={
            "username": "loginuser",
            "password": "password123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "loginuser"
        assert data["user"]["email"] == "login@example.com"

    def test_login_wrong_password(self, client, db):
        """错误密码登录返回 401"""
        user_service.register(
            db, "loginuser2", "login2@example.com", "password123")
        response = client.post("/api/auth/login", json={
            "username": "loginuser2",
            "password": "wrongpassword",
        })
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """不存在用户登录返回 401"""
        response = client.post("/api/auth/login", json={
            "username": "nobody",
            "password": "password123",
        })
        assert response.status_code == 401

    def test_login_missing_fields(self, client):
        """缺少必填字段返回 422"""
        response = client.post("/api/auth/login", json={
            "username": "test",
        })
        assert response.status_code == 422

    # ── 获取当前用户接口测试 ──────────────────────

    def test_me_authenticated(self, client, db):
        """GET /api/auth/me 认证后获取用户信息"""
        user_service.register(db, "meuser", "me@example.com", "password123")
        login_resp = client.post("/api/auth/login", json={
            "username": "meuser",
            "password": "password123",
        })
        token = login_resp.json()["access_token"]
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "meuser"
        assert data["email"] == "me@example.com"

    def test_me_no_token(self, client):
        """无 Token 请求 /api/auth/me 返回 401"""
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_me_invalid_token(self, client):
        """无效 Token 返回 401"""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    def test_me_wrong_scheme(self, client):
        """错误认证方案返回 401"""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Basic dGVzdDp0ZXN0"},
        )
        assert response.status_code == 401

    # ── 完整流程测试 ──────────────────────────────

    def test_full_auth_flow(self, client):
        """完整注册 -> 登录 -> 获取用户流程"""
        # 1. 注册
        reg_resp = client.post("/api/auth/register", json={
            "username": "flowuser",
            "email": "flow@example.com",
            "password": "password123",
        })
        assert reg_resp.status_code == 201

        # 2. 登录
        login_resp = client.post("/api/auth/login", json={
            "username": "flowuser",
            "password": "password123",
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]

        # 3. 获取用户信息
        me_resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["username"] == "flowuser"
