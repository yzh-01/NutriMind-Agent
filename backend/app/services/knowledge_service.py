import os
import tempfile
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy import text

from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class KnowledgeService:
    def __init__(self):
        self.embeddings = None
        self.vector_store = None
        self.text_splitter = None
        self._initialized = False

    def _initialize(self):
        """延迟初始化，避免启动时加载依赖"""
        if self._initialized:
            return

        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            from langchain_openai import OpenAIEmbeddings
            from langchain_community.vectorstores import PGVector

            # 1. 初始化 Embeddings
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_BASE_URL,
                model="Qwen/Qwen3-Embedding-8B"
            )

            # 2. 初始化文本分割器
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
                separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
            )

            # 3. 初始化向量存储
            self._init_vector_store()

            self._initialized = True
            logger.info("知识库服务初始化完成")
        except Exception as e:
            logger.error(f"知识库服务初始化失败: {e}")
            raise

    def _init_vector_store(self):
        """初始化 PgVector"""
        from langchain_community.vectorstores import PGVector
        connection_string = settings.DATABASE_URL
        self.vector_store = PGVector(
            connection_string=connection_string,
            embedding_function=self.embeddings,
            collection_name="knowledge_base",
            pre_delete_collection=False
        )
        logger.info("PgVector 向量存储初始化完成")

    def load_document(self, file_path: str) -> List[Any]:
        """加载文档，根据扩展名选择加载器"""
        self._initialize()
        file_ext = Path(file_path).suffix.lower()
        try:
            if file_ext == ".pdf":
                from langchain_community.document_loaders import PyPDFLoader
                loader = PyPDFLoader(file_path)
            elif file_ext == ".md":
                from langchain_community.document_loaders import UnstructuredMarkdownLoader
                loader = UnstructuredMarkdownLoader(file_path)
            elif file_ext in [".txt", ".text"]:
                from langchain_community.document_loaders import TextLoader
                loader = TextLoader(file_path, encoding="utf-8")
            elif file_ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]:
                # 图片文件使用多模态模型提取描述
                return self._process_image(file_path)
            else:
                logger.warning(f"不支持的文件类型：{file_ext}")
                return []
            documents = loader.load()
            logger.info(f"加载文档成功：{file_path}，页数/文档数={len(documents)}")
            return documents
        except Exception as e:
            logger.error(f"加载文档失败 {file_path}: {e}")
            return []

    def _process_image(self, file_path: str) -> List[Any]:
        """使用多模态模型提取图片描述"""
        from langchain_core.documents import Document
        from app.config.settings import settings
        import base64
        
        try:
            # 读取图片并转为 base64
            with open(file_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            
            # 使用 OpenAI API 调用多模态模型
            from openai import OpenAI
            
            client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL
            )
            
            # 构建消息
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_data}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "请详细描述这张图片的内容，包括场景、物体、文字等信息。"
                        }
                    ]
                }
            ]
            
            # 调用模型
            response = client.chat.completions.create(
                model="Qwen/Qwen3-VL-8B-Instruct",
                messages=messages,
                max_tokens=500
            )
            
            # 提取描述文本
            description = response.choices[0].message.content
            
            logger.info(f"图片描述提取成功：{file_path}")
            
            # 返回 Document 对象
            doc = Document(
                page_content=description,
                metadata={
                    "source": file_path,
                    "file_name": Path(file_path).name,
                    "type": "image"
                }
            )
            return [doc]
            
        except Exception as e:
            logger.error(f"图片处理失败 {file_path}: {e}")
            return []

    def split_document(self, documents: List[Any]) -> List[Any]:
        """文档分块"""
        self._initialize()
        try:
            chunks = self.text_splitter.split_documents(documents)
            logger.info(f"文档分块完成：原始={len(documents)}，分块后={len(chunks)}")
            return chunks
        except Exception as e:
            logger.error(f"文档分块失败: {e}")
            return []

    async def embed_and_store(self, file_path: str, user_id: int = 0) -> int:
        """加载、分块、向量化并存储文档"""
        self._initialize()
        try:
            # 加载文档（同步操作，放在线程池执行）
            import asyncio
            documents = await asyncio.to_thread(self.load_document, file_path)
            if not documents:
                return 0

            chunks = await asyncio.to_thread(self.split_document, documents)
            if not chunks:
                return 0

            # 添加元数据（含 user_id 用于用户隔离）
            for chunk in chunks:
                chunk.metadata["source"] = file_path
                chunk.metadata["file_name"] = Path(file_path).name
                chunk.metadata["user_id"] = str(user_id)

            # 存储到向量库（add_documents 是同步方法，但可能耗时）
            await asyncio.to_thread(self.vector_store.add_documents, chunks)
            logger.info(f"文档存储完成: {file_path}, 块数={len(chunks)}")
            return len(chunks)
        except Exception as e:
            logger.error(f"向量化存储失败: {e}")
            return 0

    async def search(self, query: str, k: int = 5, user_id: int = 0) -> List[Dict[str, Any]]:
        """语义检索（可选按用户过滤）。"""
        self._initialize()
        try:
            import asyncio
            # 多取一些结果再过滤，保证返回 k 条
            fetch_k = k * 3 if user_id else k
            results = await asyncio.to_thread(
                self.vector_store.similarity_search_with_score, query, k=fetch_k
            )
            formatted = []
            for doc, score in results:
                if user_id and doc.metadata.get("user_id") != str(user_id):
                    continue
                formatted.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score)
                })
                if len(formatted) >= k:
                    break
            logger.info(f"知识库检索完成: query={query[:50]}..., 结果数={len(formatted)}")
            return formatted
        except Exception as e:
            logger.error(f"知识库检索失败: {e}")
            return []

    async def delete_by_source(self, source: str, user_id: int = 0) -> bool:
        """按来源删除文档（仅允许删除自己上传的）。"""
        self._initialize()
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(settings.DATABASE_URL)
            with engine.connect() as conn:
                sql = text(
                    "DELETE FROM langchain_pg_embedding "
                    "WHERE cmetadata->>'source' = :source "
                    "AND cmetadata->>'user_id' = :user_id"
                )
                result = conn.execute(sql, {"source": source, "user_id": str(user_id)})
                conn.commit()
                deleted = result.rowcount
                logger.info(f"删除文档 {source}，共删除 {deleted} 个块")
                return deleted > 0
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False

    async def get_collection_stats(self, user_id: int = 0) -> Dict[str, Any]:
        """获取统计信息（可选按用户过滤）。"""
        self._initialize()
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(settings.DATABASE_URL)
            with engine.connect() as conn:
                if user_id:
                    count_sql = text(
                        "SELECT COUNT(*) FROM langchain_pg_embedding "
                        "WHERE cmetadata->>'user_id' = :uid"
                    )
                    total = conn.execute(count_sql, {"uid": str(user_id)}).scalar() or 0
                    group_sql = text(
                        "SELECT cmetadata->>'source' as source, COUNT(*) as count "
                        "FROM langchain_pg_embedding "
                        "WHERE cmetadata->>'user_id' = :uid "
                        "GROUP BY cmetadata->>'source'"
                    )
                    rows = conn.execute(group_sql, {"uid": str(user_id)}).fetchall()
                else:
                    count_sql = text("SELECT COUNT(*) FROM langchain_pg_embedding")
                    total = conn.execute(count_sql).scalar() or 0
                    group_sql = text(
                        "SELECT cmetadata->>'source' as source, COUNT(*) as count "
                        "FROM langchain_pg_embedding "
                        "GROUP BY cmetadata->>'source'"
                    )
                    rows = conn.execute(group_sql).fetchall()
                sources = [{"source": row[0], "count": row[1]} for row in rows]
                return {"total_chunks": total, "sources": sources}
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {"total_chunks": 0, "sources": []}

# 全局单例
knowledge_service = KnowledgeService()