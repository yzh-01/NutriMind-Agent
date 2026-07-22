import os
import tempfile
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import text

from app.config.settings import settings
from app.services.web_search_service import web_search_service
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

    async def embed_and_store(self, file_path: str, user_id: int = 0) -> Dict[str, int]:
        """加载、分块、向量化并存储文档。

        返回 {"chunks_count": 向量分块数, "foods_count": 抽取入图谱的食物数}。
        文档入向量库后，会额外抽取“食物-营养-分类”实体写入 food_nutrition，
        使上传的资料自动出现在营养知识图谱中。抽取失败不影响向量入库。
        """
        try:
            self._initialize()
            # 加载文档（同步操作，放在线程池执行）
            import asyncio
            documents = await asyncio.to_thread(self.load_document, file_path)
            if not documents:
                return {"chunks_count": 0, "foods_count": 0}

            chunks = await asyncio.to_thread(self.split_document, documents)
            if not chunks:
                return {"chunks_count": 0, "foods_count": 0}

            # 添加元数据（含 user_id 用于用户隔离）
            for chunk in chunks:
                chunk.metadata["source"] = file_path
                chunk.metadata["file_name"] = Path(file_path).name
                chunk.metadata["user_id"] = str(user_id)

            # 存储到向量库（add_documents 是同步方法，但可能耗时）
            await asyncio.to_thread(self.vector_store.add_documents, chunks)
            logger.info(f"文档存储完成: {file_path}, 块数={len(chunks)}")

            # 从文档正文抽取食物实体并写入图谱数据表（best-effort，失败不影响上传）
            foods_count = 0
            try:
                full_text = "\n".join(doc.page_content for doc in documents)
                foods_count = await self.extract_and_store_graph(
                    full_text, source=Path(file_path).name
                )
            except Exception as exc:
                logger.warning("图谱实体抽取失败，不影响文档入库: %s", exc)

            return {"chunks_count": len(chunks), "foods_count": foods_count}
        except Exception as e:
            logger.error(f"向量化存储失败: {e}")
            return {"chunks_count": 0, "foods_count": 0}

    # 抽取正文时最多送入模型的字符数，控制单次调用成本与延迟
    _EXTRACT_MAX_CHARS = 6000
    # 单次回填处理的资料上限，避免一次请求意外产生过多模型调用
    _REBUILD_MAX_SOURCES = 24

    async def extract_and_store_graph(self, text: str, source: str = "") -> int:
        """从文档正文抽取食物营养实体，并写入 food_nutrition 图谱数据表。

        返回新增/更新的食物条目数量。抽取由大模型完成，仅提取文中明确
        提及、且带营养语境的食物，避免臆造数据。
        """
        import asyncio

        if not text or not text.strip():
            return 0
        foods = await asyncio.to_thread(self._extract_food_entities, text[: self._EXTRACT_MAX_CHARS])
        if not foods:
            return 0
        return await asyncio.to_thread(self._store_food_entities, foods, source)

    async def rebuild_graph_from_knowledge(self, user_id: int = 0) -> Dict[str, int]:
        """从已入库的向量文档回填营养图谱。

        这用于处理功能上线前已经上传的资料。向量表按资料名聚合后，
        每份资料只调用一次实体抽取，避免对每个分块重复调用模型。
        """
        import asyncio

        source_texts = await asyncio.to_thread(self._load_graph_source_texts, user_id)
        processed_sources = 0
        foods_count = 0
        for source, text in source_texts[: self._REBUILD_MAX_SOURCES]:
            foods_count += await self.extract_and_store_graph(text, source=source)
            processed_sources += 1

        logger.info(
            "知识库图谱回填完成：资料=%d，新增/更新食物=%d",
            processed_sources,
            foods_count,
        )
        return {"processed_sources": processed_sources, "foods_count": foods_count}

    @staticmethod
    def _load_graph_source_texts(user_id: int = 0) -> List[Tuple[str, str]]:
        """按资料聚合 PgVector 中的文档正文，供图谱回填使用。"""
        from sqlalchemy import create_engine, text

        engine = create_engine(settings.DATABASE_URL)
        query = text(
            "SELECT document, "
            "COALESCE(cmetadata->>'file_name', cmetadata->>'source', '知识库文档') "
            "AS source_name "
            "FROM langchain_pg_embedding "
            "WHERE (:include_all OR cmetadata->>'user_id' = :user_id) "
            "ORDER BY source_name"
        )
        grouped: Dict[str, List[str]] = {}
        with engine.connect() as conn:
            rows = conn.execute(
                query,
                {"include_all": user_id == 0, "user_id": str(user_id)},
            ).fetchall()
        for document, source_name in rows:
            if not document:
                continue
            source = str(source_name or "知识库文档")
            grouped.setdefault(source, []).append(str(document))
        return [(source, "\n".join(chunks)) for source, chunks in grouped.items()]

    def _extract_food_entities(self, text: str) -> List[Dict[str, Any]]:
        """调用大模型，从文本抽取结构化食物营养实体（每 100g）。"""
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_BASE_URL,
            temperature=0,
            max_tokens=1500,
        )
        prompt = (
            "你是营养知识图谱抽取器。从下面的资料中提取被明确讨论、且带营养语境的食物，"
            "为每种食物给出【每 100g】的营养数据。严格要求：\n"
            "1. 只提取资料中真实出现的食物，不要臆造；资料未涉及食物时返回空数组。\n"
            "2. 所有营养数值必须是【每 100g】的标准值，单位固定为 kcal 或 g：\n"
            "   - 资料给的是某个份量的总量时（如『200g 鸡胸肉含蛋白质 62g』），"
            "必须换算回每 100g（62÷200×100=31），绝不直接照抄份量总量。\n"
            "   - 资料本身就是每 100g 值时，直接使用。\n"
            "   - 资料没给数值时，用该食物公认的每 100g 标准值；无法确定的字段填 null，绝不编造。\n"
            "3. category 用简体中文大类：水果/蔬菜/肉蛋类/谷物/豆类/坚果/乳制品/水产/主食/其他。\n"
            "4. 只返回 JSON，不要解释、不要代码块围栏。所有数值均为每 100g，格式：\n"
            '{"foods": [{"name_en": "apple", "name_cn": "苹果", "category": "水果", '
            '"calories": 52, "protein": 0.3, "fat": 0.2, "carbs": 13.8, "fiber": 2.4}]}\n\n'
            "资料：\n" + text
        )
        try:
            response = llm.invoke(prompt)
            raw = response.content if hasattr(response, "content") else str(response)
            foods = self._parse_food_json(raw)
            logger.info("图谱实体抽取完成：识别食物 %d 种", len(foods))
            return foods
        except Exception as exc:
            logger.warning("食物实体抽取调用失败: %s", exc)
            return []

    @staticmethod
    def _parse_food_json(raw: str) -> List[Dict[str, Any]]:
        """稳健解析模型返回的 JSON（容忍代码块围栏与前后噪声）。"""
        import json
        import re

        if not raw or not isinstance(raw, str):
            return []
        cleaned = raw.strip()
        # 去掉 ```json ... ``` 围栏
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned).strip()
        # 截取最外层 JSON 对象
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            cleaned = cleaned[start : end + 1]
        try:
            data = json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            return []
        foods = data.get("foods") if isinstance(data, dict) else data
        return foods if isinstance(foods, list) else []

    def _store_food_entities(self, foods: List[Dict[str, Any]], source: str) -> int:
        """将抽取到的食物实体去重后 upsert 进 food_nutrition。"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.entity.db_models import FoodNutrition

        def _num(value):
            try:
                num = float(value)
            except (TypeError, ValueError):
                return None
            return num if num >= 0 else None

        engine = create_engine(settings.DATABASE_URL)
        Session = sessionmaker(bind=engine)
        db = Session()
        stored = 0
        try:
            for item in foods:
                if not isinstance(item, dict):
                    continue
                name_cn = str(item.get("name_cn") or "").strip()
                name_en = str(item.get("name_en") or "").strip().lower()
                if not name_cn and not name_en:
                    continue
                calories = _num(item.get("calories"))
                # 无中文名或无热量的条目信息量不足，跳过（热量是图谱主营养边）
                if not name_cn or calories is None:
                    continue

                existing = (
                    db.query(FoodNutrition)
                    .filter(
                        (FoodNutrition.food_name_cn == name_cn)
                        | ((FoodNutrition.food_name == name_en) & (name_en != ""))
                    )
                    .first()
                )
                category = str(item.get("category") or "").strip() or None
                protein = _num(item.get("protein"))
                fat = _num(item.get("fat"))
                carbs = _num(item.get("carbs"))
                fiber = _num(item.get("fiber"))

                if existing is None:
                    db.add(FoodNutrition(
                        food_name=name_en or name_cn,
                        food_name_cn=name_cn,
                        calories_per_100g=calories,
                        protein_per_100g=protein or 0.0,
                        fat_per_100g=fat or 0.0,
                        carbs_per_100g=carbs or 0.0,
                        fiber_per_100g=fiber or 0.0,
                        category=category,
                        source=source or "知识库抽取",
                    ))
                    stored += 1
                else:
                    changed = False
                    updates = {
                        "calories_per_100g": calories,
                        "protein_per_100g": protein,
                        "fat_per_100g": fat,
                        "carbs_per_100g": carbs,
                        "fiber_per_100g": fiber,
                    }
                    for field, value in updates.items():
                        if value is not None and getattr(existing, field) != value:
                            setattr(existing, field, value)
                            changed = True
                    if category and existing.category != category:
                        existing.category = category
                        changed = True
                    if name_en and existing.food_name != name_en:
                        existing.food_name = name_en
                        changed = True
                    if changed:
                        existing.source = source or existing.source or "知识库抽取"
                        stored += 1
            db.commit()
            logger.info("图谱食物入库完成：新增/更新 %d 条（来源=%s）", stored, source)
            return stored
        except Exception as exc:
            db.rollback()
            logger.error("图谱食物入库失败: %s", exc)
            return 0
        finally:
            db.close()

    async def search(self, query: str, k: int = 5, user_id: int = 0) -> List[Dict[str, Any]]:
        """语义检索（可选按用户过滤）。"""
        try:
            self._initialize()
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

    async def store_web_results(self, query: str, results: List[Dict[str, Any]], user_id: int) -> int:
        """把联网检索语料写入用户向量库，供后续 RAG 复用。"""
        if not results:
            return 0
        self._initialize()
        from langchain_core.documents import Document
        import asyncio

        documents = []
        for item in results:
            content = item.get("content", "").strip()
            if not content:
                continue
            documents.append(Document(page_content=content, metadata={
                "source": item.get("url") or "exa",
                "file_name": item.get("title") or "联网检索",
                "title": item.get("title"),
                "url": item.get("url"),
                "source_type": "web",
                "provider": item.get("provider", "exa"),
                "query": query,
                "user_id": str(user_id),
            }))
        if not documents:
            return 0
        await asyncio.to_thread(self.vector_store.add_documents, documents)
        return len(documents)

    async def retrieve_with_fallback(
        self,
        query: str,
        k: int = 5,
        user_id: int = 0,
        verify_web: bool = False,
        store_web: bool = True,
    ) -> Dict[str, Any]:
        """先查私有知识库；结果不足时联网，并可用网页来源交叉验证。"""
        local_results = await self.search(query, k=k, user_id=user_id)
        best_score = min((item.get("score", float("inf")) for item in local_results), default=float("inf"))
        needs_fallback = not local_results or best_score > settings.KNOWLEDGE_LOCAL_SCORE_THRESHOLD
        web_results = []
        if needs_fallback or verify_web:
            web_results = await web_search_service.search(query, limit=k)
            if web_results and store_web and settings.WEB_SEARCH_STORE_RESULTS:
                try:
                    await self.store_web_results(query, web_results, user_id)
                except Exception as exc:
                    logger.warning("联网语料落库失败，不影响本次回答: %s", exc)
        return {
            "local_results": local_results,
            "web_results": web_results,
            "used_web_fallback": needs_fallback and bool(web_results),
            "cross_verified": bool(local_results and web_results),
        }

    async def answer(
        self,
        query: str,
        k: int = 5,
        user_id: int = 0,
        verify_web: bool = False,
        store_web: bool = True,
    ) -> Dict[str, Any]:
        """RAG 问答：返回自然语言回答和可展示的关联来源。"""
        retrieved = await self.retrieve_with_fallback(query, k, user_id, verify_web, store_web)
        sources = []
        contexts = []
        for index, item in enumerate(retrieved["local_results"], 1):
            metadata = item.get("metadata", {})
            sources.append({
                "id": f"local-{index}", "type": "knowledge",
                "title": metadata.get("file_name") or metadata.get("source") or "知识库文档",
                "url": metadata.get("url"), "score": item.get("score"),
                "excerpt": item.get("content", "")[:300],
            })
            contexts.append(f"[local-{index}] {item.get('content', '')}")
        for index, item in enumerate(retrieved["web_results"], 1):
            sources.append({
                "id": f"web-{index}", "type": "web", "title": item.get("title"),
                "url": item.get("url"), "score": None,
                "excerpt": item.get("content", "")[:300],
            })
            contexts.append(f"[web-{index}] {item.get('content', '')}")

        if not contexts:
            return {"answer": "当前知识库和联网检索均未找到足够可靠的相关资料。请换一种问法，或先上传相关营养资料。", "sources": [], **retrieved}

        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=settings.OPENAI_MODEL, openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_BASE_URL, temperature=0.2,
        )
        prompt = (
            "你是严谨的营养知识助手。只根据下列资料回答问题，写成一段清晰、完整的中文回答；"
            "重要结论后用 [local-1] 或 [web-1] 标注来源。资料冲突时明确指出，不要编造。"
            "这不是医疗诊断。\n\n问题：" + query + "\n\n资料：\n" + "\n\n".join(contexts)
        )
        response = await llm.ainvoke(prompt)
        return {"answer": str(response.content), "sources": sources, **retrieved}

    async def delete_by_source(self, source: str, user_id: int = 0) -> bool:
        """按来源删除文档（仅允许删除自己上传的）。"""
        try:
            self._initialize()
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
        try:
            self._initialize()
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

    async def get_knowledge_graph(self) -> Dict[str, Any]:
        """构建营养知识图谱（基于 food_nutrition 表）。
        返回 nodes 和 edges 供前端可视化渲染。
        """
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(settings.DATABASE_URL)
            with engine.connect() as conn:
                rows = conn.execute(
                    text("SELECT * FROM food_nutrition ORDER BY category, food_name_cn")
                ).fetchall()

            nodes = []
            edges = []
            seen_cats = set()
            nutrients = [
                ("calories", "热量", "kcal"),
                ("protein", "蛋白质", "g"),
                ("fat", "脂肪", "g"),
                ("carbs", "碳水化合物", "g"),
                ("fiber", "膳食纤维", "g"),
            ]
            col_map = {"calories": 3, "protein": 4, "fat": 5, "carbs": 6, "fiber": 7}

            for nid, nlabel, unit in nutrients:
                nodes.append({
                    "id": f"nut_{nid}", "label": nlabel,
                    "type": "nutrient", "unit": unit, "group": "nutrient",
                })

            for row in rows:
                fid = f"food_{row[0]}"
                cat = row[11] or "未分类"
                cid = f"cat_{cat}"

                if cid not in seen_cats:
                    nodes.append({
                        "id": cid, "label": cat,
                        "type": "category", "group": "category",
                    })
                    seen_cats.add(cid)

                nodes.append({
                    "id": fid, "label": row[2], "name_en": row[1],
                    "type": "food", "group": "food",
                    "category": cat,
                    "calories": row[3], "protein": row[4],
                    "fat": row[5], "carbs": row[6], "fiber": row[7],
                })

                edges.append({"source": fid, "target": cid, "relation": "BELONGS_TO"})

                for nid, _, _ in nutrients:
                    val = row[col_map[nid]]
                    if val and val > 0:
                        edges.append({
                            "source": fid, "target": f"nut_{nid}",
                            "relation": "HAS_NUTRIENT", "value": float(val),
                        })

            return {"nodes": nodes, "edges": edges}
        except Exception as e:
            logger.error(f"构建知识图谱失败: {e}")
            return {"nodes": [], "edges": []}


# 全局单例
knowledge_service = KnowledgeService()
