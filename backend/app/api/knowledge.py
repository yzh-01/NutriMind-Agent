import os
import tempfile
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.entity.schemas import ApiResponse
from app.services.knowledge_service import knowledge_service

from app.core.security import get_current_user
from app.entity.db_models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/knowledge", tags=["知识库"])

ALLOWED_EXTENSIONS = {".pdf", ".md", ".txt", ".text"}

@router.post("/upload", response_model=ApiResponse)
async def upload_document(
    file: UploadFile = File(..., description="文档文件 (PDF/MD/TXT)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """上传文档"""
    # 1. 检查文件类型
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型：{file_ext}，支持：{', '.join(ALLOWED_EXTENSIONS)}"
        )

    # 2. 保存临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # 3. 上传到知识库
        chunks_count = await knowledge_service.embed_and_store(tmp_path)
        if chunks_count == 0:
            raise HTTPException(status_code=400, detail="文档处理失败，未生成有效内容")

        # 4. 返回结果
        return ApiResponse(
            code=200,
            message="文档上传成功",
            data={
                "filename": file.filename,
                "chunks_count": chunks_count
            }
        )
    finally:
        # 5. 清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

@router.get("/search", response_model=ApiResponse)
async def search_knowledge(
    query: str = ...,
    k: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """检索知识库"""
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="查询内容不能为空")

    try:
        results = await knowledge_service.search(query, k=k)
        return ApiResponse(
            code=200,
            data={
                "query": query,
                "results": results,
                "total": len(results)
            }
        )
    except Exception as e:
        logger.error(f"知识库检索失败: {e}")
        raise HTTPException(status_code=500, detail=f"检索失败: {str(e)}")

@router.delete("/", response_model=ApiResponse)
async def delete_document(
    source: str = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除指定来源的文档"""
    if not source or not source.strip():
        raise HTTPException(status_code=400, detail="文档来源不能为空")

    try:
        success = await knowledge_service.delete_by_source(source)
        if not success:
            raise HTTPException(status_code=404, detail="未找到指定文档")
        return ApiResponse(code=200, message="文档删除成功")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@router.get("/stats", response_model=ApiResponse)
async def get_knowledge_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取知识库统计信息"""
    try:
        stats = await knowledge_service.get_collection_stats()
        return ApiResponse(code=200, data=stats)
    except Exception as e:
        logger.error(f"获取知识库统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")