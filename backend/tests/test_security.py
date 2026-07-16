"""
安全模块测试：密码哈希、JWT Token 生成与验证
"""
import pytest
from app.core.security import (
    hash_password, verify_password,
    create_access_token, decode_access_token,
)


class TestPasswordHashing:
    """密码哈希与校验测试"""

    def test_hash_and_verify(self):
        """正常场景：哈希后可以校验成功"""
        password = "my_secure_password"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed) is True

    def test_wrong_password(self):
        """错误密码校验失败"""
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_different_passwords_have_different_hashes(self):
        """相同密码两次哈希结果不同（salt 随机）"""
        password = "same_password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    def test_empty_password(self):
        """空密码也能正常处理"""
        hashed = hash_password("")
        assert verify_password("", hashed) is True

    def test_unicode_password(self):
        """中文密码支持"""
        password = "中文密码测试123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_long_password_truncation(self):
        """超过 72 字节的密码被截断处理"""
        password = "a" * 100
        hashed = hash_password(password)
        # 截断后校验应该通过
        assert verify_password(password, hashed) is True


class TestJWT:
    """JWT Token 测试"""

    def test_create_and_decode_token(self):
        """生成 Token 后能正确解码"""
        data = {"sub": "1"}
        token = create_access_token(data)
        decoded = decode_access_token(token)
        assert decoded["sub"] == "1"

    def test_token_contains_expiry(self):
        """Token 包含过期时间"""
        token = create_access_token({"sub": "1"})
        decoded = decode_access_token(token)
        assert "exp" in decoded

    def test_decode_invalid_token(self):
        """无效 Token 解码抛出异常"""
        from jose import JWTError
        with pytest.raises(JWTError):
            decode_access_token("invalid.token.here")

    def test_token_with_custom_data(self):
        """自定义载荷数据保留"""
        data = {"sub": "42", "role": "admin", "scope": "detection:write"}
        token = create_access_token(data)
        decoded = decode_access_token(token)
        assert decoded["sub"] == "42"
        assert decoded["role"] == "admin"
        assert decoded["scope"] == "detection:write"

    def test_different_users_have_different_tokens(self):
        """不同用户生成不同 Token"""
        token1 = create_access_token({"sub": "1"})
        token2 = create_access_token({"sub": "2"})
        assert token1 != token2
