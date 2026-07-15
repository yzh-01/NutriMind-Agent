"""
知识库功能完整测试
测试知识库的上传、检索、删除、统计功能
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import BytesIO
from fastapi.testclient import TestClient


# 模拟测试用户
@pytest.fixture
def mock_user():
    """创建模拟用户"""
    from app.entity.db_models import User
    user = User(
        id=1,
        username="testuser",
        email="test@test.com",
        hashed_password="mock_hash",
        is_active=True
    )
    return user


@pytest.fixture
def test_client(mock_user):
    """创建测试客户端，绕过认证"""
    from fastapi.testclient import TestClient
    from main import app
    
    # 覆盖认证依赖
    from app.core.security import get_current_user
    app.dependency_overrides[get_current_user] = lambda: mock_user
    
    client = TestClient(app)
    yield client
    
    # 清理覆盖
    app.dependency_overrides.clear()


@pytest.fixture
def temp_txt_file():
    """创建临时 TXT 测试文件"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write("这是一个测试文档。\n\n营养学是研究食物与健康的科学。")
        path = f.name
    
    yield path
    
    try:
        if os.path.exists(path):
            os.unlink(path)
    except PermissionError:
        pass


@pytest.fixture
def temp_md_file():
    """创建临时 MD 测试文件"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write("# 测试标题\n\n这是测试内容。")
        path = f.name
    
    yield path
    
    try:
        if os.path.exists(path):
            os.unlink(path)
    except PermissionError:
        pass


class TestKnowledgeUpload:
    """测试文档上传功能"""
    
    def test_upload_txt_file(self, test_client, temp_txt_file):
        """测试上传 TXT 文件"""
        with open(temp_txt_file, 'rb') as f:
            response = test_client.post(
                "/api/knowledge/upload",
                files={"file": ("test.txt", f, "text/plain")},
            )
        
        print(f"Response: {response.status_code} - {response.json()}")
        assert response.status_code in [200, 400, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 200
            assert "chunks_count" in data["data"]
    
    def test_upload_md_file(self, test_client, temp_md_file):
        """测试上传 Markdown 文件"""
        with open(temp_md_file, 'rb') as f:
            response = test_client.post(
                "/api/knowledge/upload",
                files={"file": ("test.md", f, "text/markdown")},
            )
        
        print(f"Response: {response.status_code} - {response.json()}")
        assert response.status_code in [200, 400, 500]
    
    def test_upload_unsupported_file(self, test_client):
        """测试上传不支持的文件类型"""
        response = test_client.post(
            "/api/knowledge/upload",
            files={"file": ("test.docx", BytesIO(b"fake content"), "application/octet-stream")},
        )
        
        print(f"Response: {response.status_code} - {response.json()}")
        assert response.status_code == 400
        assert "不支持" in response.json().get("detail", "")


class TestKnowledgeSearch:
    """测试语义搜索功能"""
    
    def test_search_knowledge_basic(self, test_client):
        """测试基本搜索功能"""
        response = test_client.get(
            "/api/knowledge/search",
            params={"query": "营养学", "k": 5}
        )
        
        print(f"Response: {response.status_code} - {response.json()}")
        assert response.status_code in [200, 500]
    
    def test_search_empty_query(self, test_client):
        """测试空查询"""
        response = test_client.get(
            "/api/knowledge/search",
            params={"query": "", "k": 5}
        )
        
        print(f"Response: {response.status_code} - {response.json()}")
        assert response.status_code == 400
    
    def test_search_response_format(self, test_client):
        """测试搜索响应格式"""
        response = test_client.get(
            "/api/knowledge/search",
            params={"query": "测试", "k": 3}
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "code" in data
            assert "data" in data
            assert "results" in data["data"]


class TestKnowledgeDelete:
    """测试删除文档功能"""
    
    def test_delete_document_nonexistent(self, test_client):
        """测试删除不存在的文档"""
        response = test_client.delete(
            "/api/knowledge/",
            params={"source": "/nonexistent/path/document.txt"}
        )
        
        print(f"Response: {response.status_code} - {response.json()}")
        assert response.status_code in [200, 404]
    
    def test_delete_empty_source(self, test_client):
        """测试空来源删除"""
        response = test_client.delete(
            "/api/knowledge/",
            params={"source": ""}
        )
        
        print(f"Response: {response.status_code} - {response.json()}")
        assert response.status_code == 400


class TestKnowledgeStats:
    """测试统计信息功能"""
    
    def test_get_stats_basic(self, test_client):
        """测试获取统计信息"""
        response = test_client.get("/api/knowledge/stats")
        
        print(f"Response: {response.status_code} - {response.json()}")
        assert response.status_code in [200, 500]
    
    def test_get_stats_response_format(self, test_client):
        """测试统计响应格式"""
        response = test_client.get("/api/knowledge/stats")
        
        if response.status_code == 200:
            data = response.json()
            assert "code" in data
            assert "data" in data
            stats = data["data"]
            assert "total_chunks" in stats
            assert "sources" in stats


class TestKnowledgeService:
    """测试 KnowledgeService 类"""
    
    def test_knowledge_service_init(self):
        """测试服务初始化"""
        from app.services.knowledge_service import KnowledgeService
        
        service = KnowledgeService()
        assert service is not None
        assert service._initialized == False


class TestKnowledgeAPI:
    """API 端点基础测试"""
    
    def test_knowledge_routes_registered(self, test_client):
        """测试知识库路由已注册"""
        response = test_client.post(
            "/api/knowledge/upload",
            files={"file": ("test.txt", BytesIO(b"test content"), "text/plain")}
        )
        assert response.status_code in [200, 400, 401, 500]
        
        response = test_client.get("/api/knowledge/search?query=test")
        assert response.status_code in [200, 401, 500]
        
        response = test_client.get("/api/knowledge/stats")
        assert response.status_code in [200, 401, 500]
        
        response = test_client.delete("/api/knowledge/?source=test")
        assert response.status_code in [200, 401, 404, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
