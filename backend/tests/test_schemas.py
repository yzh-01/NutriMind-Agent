"""
Pydantic Schema 模型测试：请求验证、序列化、约束
"""
import pytest
from pydantic import ValidationError
from app.entity.schemas import (
    UserRegister, UserLogin, TokenResponse, UserResponse,
    ApiResponse, PaginationParams,
)


class TestUserRegister:
    """用户注册 Schema 验证"""

    def test_valid_register(self):
        """有效注册数据"""
        data = UserRegister(
            username="testuser",
            email="test@example.com",
            password="password123",
        )
        assert data.username == "testuser"
        assert data.email == "test@example.com"
        assert data.password == "password123"

    def test_username_too_short(self):
        """用户名过短（< 3）"""
        with pytest.raises(ValidationError):
            UserRegister(username="ab", email="test@example.com",
                         password="password123")

    def test_username_too_long(self):
        """用户名过长（> 50）"""
        with pytest.raises(ValidationError):
            UserRegister(
                username="a" * 51,
                email="test@example.com",
                password="password123",
            )

    def test_password_too_short(self):
        """密码过短（< 6）"""
        with pytest.raises(ValidationError):
            UserRegister(username="testuser",
                         email="test@example.com", password="12345")

    def test_missing_username(self):
        """缺少用户名"""
        with pytest.raises(ValidationError):
            UserRegister(email="test@example.com", password="password123")

    def test_missing_email(self):
        """缺少邮箱"""
        with pytest.raises(ValidationError):
            UserRegister(username="testuser", password="password123")

    def test_missing_password(self):
        """缺少密码"""
        with pytest.raises(ValidationError):
            UserRegister(username="testuser", email="test@example.com")

    def test_invalid_email(self):
        """无效邮箱格式"""
        with pytest.raises(ValidationError):
            UserRegister(username="testuser", email="not-an-email",
                         password="password123")


class TestUserLogin:
    """用户登录 Schema 验证"""

    def test_valid_login(self):
        """有效登录数据"""
        data = UserLogin(username="testuser", password="password123")
        assert data.username == "testuser"
        assert data.password == "password123"

    def test_missing_username(self):
        """缺少用户名"""
        with pytest.raises(ValidationError):
            UserLogin(password="password123")

    def test_missing_password(self):
        """缺少密码"""
        with pytest.raises(ValidationError):
            UserLogin(username="testuser")


class TestApiResponse:
    """通用 API 响应 Schema"""

    def test_default_values(self):
        """默认值"""
        resp = ApiResponse()
        assert resp.code == 200
        assert resp.message == "success"
        assert resp.data is None

    def test_custom_values(self):
        """自定义值"""
        resp = ApiResponse(code=404, message="not found", data={"id": 1})
        assert resp.code == 404
        assert resp.message == "not found"
        assert resp.data == {"id": 1}


class TestPaginationParams:
    """分页参数 Schema"""

    def test_default_values(self):
        """默认分页参数"""
        params = PaginationParams()
        assert params.page == 1
        assert params.page_size == 20

    def test_custom_values(self):
        """自定义分页参数"""
        params = PaginationParams(page=3, page_size=50)
        assert params.page == 3
        assert params.page_size == 50

    def test_invalid_page(self):
        """无效页码（< 1）"""
        with pytest.raises(ValidationError):
            PaginationParams(page=0)

    def test_invalid_page_size(self):
        """无效页大小（> 100）"""
        with pytest.raises(ValidationError):
            PaginationParams(page_size=101)
