"""
用户服务层测试：注册、登录、角色管理
"""
import pytest
from fastapi import HTTPException
from app.services.user_service import user_service
from app.entity.db_models import User


class TestUserRegister:
    """用户注册测试"""

    def test_register_success(self, db):
        """正常注册成功"""
        user = user_service.register(
            db=db,
            username="testuser",
            email="test@example.com",
            password="password123",
        )
        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.hashed_password != "password123"
        assert user.is_active is True
        assert user.is_superuser is False

    def test_register_duplicate_username(self, db):
        """重复用户名注册失败"""
        user_service.register(db, "testuser", "a@example.com", "password123")
        with pytest.raises(HTTPException) as exc:
            user_service.register(
                db, "testuser", "b@example.com", "password123")
        assert exc.value.status_code == 400
        assert "用户名已存在" in exc.value.detail

    def test_register_duplicate_email(self, db):
        """重复邮箱注册失败"""
        user_service.register(db, "user1", "test@example.com", "password123")
        with pytest.raises(HTTPException) as exc:
            user_service.register(
                db, "user2", "test@example.com", "password123")
        assert exc.value.status_code == 400
        assert "邮箱已被注册" in exc.value.detail

    def test_register_minimal_password(self, db):
        """6 位密码注册成功"""
        user = user_service.register(
            db, "minimal", "min@example.com", "123456")
        assert user.id is not None


class TestUserLogin:
    """用户登录测试"""

    def test_login_success(self, db):
        """正常登录成功"""
        user_service.register(
            db, "loginuser", "login@example.com", "password123")
        user = user_service.login(db, "loginuser", "password123")
        assert user.username == "loginuser"
        assert user.email == "login@example.com"

    def test_login_wrong_password(self, db):
        """错误密码登录失败"""
        user_service.register(
            db, "loginuser2", "login2@example.com", "password123")
        with pytest.raises(HTTPException) as exc:
            user_service.login(db, "loginuser2", "wrongpassword")
        assert exc.value.status_code == 401

    def test_login_nonexistent_user(self, db):
        """不存在的用户登录失败"""
        with pytest.raises(HTTPException) as exc:
            user_service.login(db, "nobody", "password123")
        assert exc.value.status_code == 401


class TestUserRoles:
    """用户角色管理测试"""

    def test_new_user_has_no_roles(self, db):
        """新注册用户默认无角色"""
        user = user_service.register(
            db, "norole", "norole@example.com", "password123")
        roles = user_service.get_user_roles(db, user)
        assert roles == []

    def test_get_user_by_id(self, db):
        """根据 ID 获取用户"""
        created = user_service.register(
            db, "byid", "byid@example.com", "password123")
        found = user_service.get_user_by_id(db, created.id)
        assert found.id == created.id
        assert found.username == "byid"

    def test_get_user_by_id_not_found(self, db):
        """不存在的用户 ID 抛出 404"""
        with pytest.raises(HTTPException) as exc:
            user_service.get_user_by_id(db, 99999)
        assert exc.value.status_code == 404


class TestTokenGeneration:
    """Token 生成测试"""

    def test_create_access_token_for_user(self, db):
        """为用户生成 JWT Token"""
        user = user_service.register(
            db, "tokenuser", "token@example.com", "password123")
        token = user_service.create_access_token_for_user(user)
        assert token is not None
        assert len(token) > 20
