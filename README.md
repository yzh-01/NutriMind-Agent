# NutriMind-Agent

> 基于 YOLOv11 食物检测 + LangGraph ReAct 智能体的 AI 营养分析平台  
> 拍一张餐食照片，系统自动识别食物种类、查询营养数据、计算热量摄入，并给出个性化饮食建议。

<p align="center">
  <strong>FastAPI</strong> · <strong>YOLO11s</strong> · <strong>LangGraph</strong> · <strong>Qwen3.6-35B-A3B</strong> · <strong>PostgreSQL + PGVector</strong>
</p>

---

## 📖 项目简介

NutriMind-Agent 是一个端到端的智能营养分析后端服务。用户上传餐食照片并附上自然语言问题，系统通过以下流程完成分析：

```text
前端上传图片 + 用户问题
  → 后端保存图片并生成 image_id
  → Agent 读取 image_id 和问题
  → Agent 调用 detect_food (YOLOv11)
  → 低置信度时 Agent 自动调用 vision_verify_food (Qwen3-VL) 兜底
  → Agent 调用 query_food_calories 查询每 100g 营养数据
  → Agent 调用 calculate_total_nutrition 汇总热量与宏量营养素
  → Agent 综合工具观察结果生成分析和建议
```

**不是固定流水线**——由 LangGraph ReAct 智能体根据用户问题自主选择并串联工具。

---

## ✨ 核心能力

| 模块 | 说明 |
|------|------|
| 🍱 YOLO 食物检测 | YOLO11s 微调，UECFOOD-256 数据集（256 类日本食物，~31,000 张标注图片），mAP@50 ≈ 72.7% |
| 🤖 LangGraph ReAct Agent | 推理 → 工具调用 → 观察 → 再推理，框架级 `recursion_limit=30` 与每轮最多 3 批工具调用保护，`MemorySaver` 进程内检查点 |
| 👁️ 视觉兜底 | 低置信度（conf < 0.25）时调用 Qwen3-VL-8B-Instruct 多模态 LLM 二次确认 |
| 📚 知识库 RAG | PGVector 向量存储，Qwen3-Embedding-8B 嵌入，支持 PDF / MD / TXT / 图片 OCR |
| 🔐 双通道认证 | JWT HS256，Bearer Header + HttpOnly Cookie，浏览器与脚本均可使用 |
| 🎯 用户档案与目标 | 身体指标（体重 / 身高 / 性别 / 活动水平）+ 健康目标（减脂 / 增肌 / 维持） |
| 🌐 联网检索 | Exa 搜索 API，本地知识库不足时自动 fallback，支持交叉验证 |
| 🖥️ 前端 | Vue 3 SPA（独立仓库），用户端 + 管理端双工作区 |

### Agent 可用工具

| 工具 | 功能 | 调用时机 |
|------|------|---------|
| `detect_food(image_id)` | YOLO 食物检测 → detections JSON | 图片对话时 Agent 自动调用 |
| `vision_verify_food(image_id)` | Qwen3-VL 视觉 LLM 兜底 | 低置信度 / YOLO 不可用时 |
| `query_food_calories(food_name)` | 查询食物每 100g 营养（模糊匹配） | 检测到食物后 |
| `query_food_by_category(category)` | 按分类浏览食物 | 用户问"水果有哪些"时 |
| `calculate_total_nutrition(food_items_json)` | 汇总热量 + 宏量营养素 | 所有食物查询完毕 |
| `save_detection_record(...)` | 保存检测记录到数据库 | 检测完成时 |
| `search_nutrition_knowledge(query)` | 检索用户知识库，本地不足时自动联网 | 营养知识问答时 |
| `search_web_evidence(query)` | Exa 联网检索营养资料 | fallback / 交叉验证 |

---

## 🏗️ 技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | FastAPI (Python 3.11+) |
| 目标检测 | Ultralytics YOLO11s |
| AI 编排 | LangGraph ReAct Agent |
| 主模型 | Qwen3.6-35B-A3B (SiliconFlow API) |
| 视觉兜底 | Qwen3-VL-8B-Instruct |
| Embedding | Qwen3-Embedding-8B |
| 数据库 | PostgreSQL + SQLAlchemy 2.0 ORM |
| 向量存储 | PGVector |
| 认证 | JWT HS256（Bearer Header + HttpOnly Cookie 双通道） |
| 包管理 | uv (`pyproject.toml`) |

---

## 📁 目录结构

```text
NutriMind-Agent/
├── README.md                       # 本文件
├── doc/                            # 设计与对齐文档
│   ├── API.md                      # 权威 API 文档
│   ├── API对齐.md                  # 认证契约对齐说明
│   └── NOMAD_AGENT_BACKEND_CHANGES.md
├── Frontend/                       # 前端已迁移至独立仓库（见下文「前端」）
└── backend/                        # 后端服务
    ├── main.py                     # FastAPI 入口，路由注册，lifespan
    ├── pyproject.toml              # Python 依赖管理 (uv)
    ├── uv.lock                     # 依赖版本锁定
    ├── Dockerfile                  # Docker 镜像
    ├── .env.example                # 环境变量模板
    ├── chat_cli.py                 # 命令行对话测试客户端
    ├── train_yolo.py               # YOLO 训练脚本 (AutoDL 优化版)
    ├── convert_uecfood.py          # UECFOOD256 → YOLO 格式转换
    ├── merge_datasets.py           # 多数据集合并
    ├── prepare_data.py             # 数据预处理
    ├── test_model.py               # 模型独立测试脚本
    ├── alembic/                    # Alembic 迁移目录（待配置）
    ├── app/
    │   ├── api/                    # 9 个路由模块
    │   │   ├── auth.py             # 注册 / 登录 / 登出 / 改密 / 当前用户
    │   │   ├── chat.py             # AI 对话（文本 + 图片 + 模拟联调）
    │   │   ├── detection.py        # YOLO 目标检测上传 + 历史查询
    │   │   ├── training.py         # 模型训练任务管理 (CRUD + 启停)
    │   │   ├── camera.py           # 摄像头图片管理
    │   │   ├── dashboard.py        # 管理看板（需 superuser）
    │   │   ├── knowledge.py        # 知识库 RAG (上传 / 检索 / 删除)
    │   │   ├── profile.py          # 用户档案 + 身体指标 + 目标
    │   │   └── health.py           # 健康检查
    │   ├── config/                 # Pydantic Settings，全局配置单例
    │   ├── core/                   # security / logger / exceptions
    │   ├── database/               # session + seed
    │   ├── entity/                 # db_models (13 张 ORM 表) + schemas (50+ Pydantic 模型)
    │   ├── middleware/             # 请求日志中间件
    │   ├── services/               # 业务逻辑层
    │   │   ├── agent_graph.py      # LangGraph ReAct Agent 编排
    │   │   ├── agent_tools.py      # 8 个 Agent 工具函数
    │   │   ├── agent_prompts.py    # 系统提示词 + 格式化
    │   │   ├── chat_service.py     # 对话会话持久化（chat_sessions / chat_messages）
    │   │   ├── detection_service.py# YOLO 模型加载 / 推理 / 结果解析
    │   │   ├── training_service.py # YOLO 训练生命周期 (后台任务)
    │   │   ├── knowledge_service.py# PGVector RAG (PDF / MD / TXT / 图片 OCR)
    │   │   ├── web_search_service.py# Exa 联网检索
    │   │   └── ...
    │   └── storage/                # minio_client / redis_client（占位）
    ├── data/
    │   ├── models/                 # YOLO 模型权重目录
    │   ├── captures/               # 摄像头图片
    │   └── agent_uploads/          # 用户上传图片临时存储
    └── tests/                      # 11 个测试文件 (pytest + SQLite)
```

---

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/yzh-01/NutriMind-Agent.git
cd NutriMind-Agent/backend
```

### 2. 安装依赖

```bash
uv sync
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY 等
```

### 4. 启动 PostgreSQL

```bash
docker run -d -p 5432:5432 \
  -e POSTGRES_USER=nutrimind-agent \
  -e POSTGRES_PASSWORD=nutrimind-agent \
  -e POSTGRES_DB=nutrimind-agent \
  postgres:16
```

### 5. 启动后端服务

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 9999 --reload
```

### 6. 运行测试

```bash
uv run pytest -v
```

---

## ⚙️ 配置说明

完整配置见 [`backend/.env.example`](backend/.env.example)，关键项：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `OPENAI_API_KEY` | - | SiliconFlow API Key |
| `OPENAI_BASE_URL` | `https://api.siliconflow.cn/v1` | LLM API 地址 |
| `OPENAI_MODEL` | `Qwen/Qwen3.6-35B-A3B` | Agent 对话模型 |
| `VISION_MODEL` | `Qwen/Qwen3-VL-8B-Instruct` | 视觉兜底模型 |
| `EXA_API_KEY` | - | Exa 联网检索 API Key |
| `WEB_SEARCH_ENABLED` | `true` | 知识库本地不足时联网 fallback |
| `KNOWLEDGE_LOCAL_SCORE_THRESHOLD` | `0.85` | 触发联网 fallback 的 PGVector 距离阈值 |
| `DETECTION_MODE` | `mock` | `mock` / `yolo` |
| `DEFAULT_DETECTION_MODEL` | `best.pt` | 模型文件名 |
| `DB_HOST` / `DB_PORT` | `localhost` / `5432` | PostgreSQL 配置 |
| `DEBUG` | `true` | `false` 关闭 mock 联调接口 |
| `ALLOWED_ORIGINS` | `localhost:3000,localhost:5173` | CORS 白名单 |

### 启用真实 YOLO 检测

```bash
# 1. 将训练好的模型放入指定目录
cp yolo11_food_best.pt backend/data/models/

# 2. 在 .env 中切换模式
DETECTION_MODE=yolo
DEFAULT_DETECTION_MODEL=yolo11_food_best.pt
```

---

## 📡 API 一览

> 完整 API 文档见 [`doc/API.md`](doc/API.md) 与 Swagger `/docs`

| 路由前缀 | 说明 |
|----------|------|
| `GET /api/health` | 健康检查（无认证） |
| `/api/auth/*` | 注册 / 登录 / 登出 / 改密 / 当前用户 |
| `POST /api/chat/message` | 文本 + 检测结果对话 |
| `POST /api/chat/image` | 图片 + 文字对话（需 YOLO 模型） |
| `POST /api/chat/mock-yolo` | 模拟 YOLO 联调（仅 DEBUG） |
| `POST /api/chat/image/mock` | 模拟图片联调（仅 DEBUG） |
| `/api/knowledge/*` | 知识库上传 / 检索 / 删除 / 统计 |
| `/api/detection/*` | 图片检测 / 场景列表 / 历史记录 |
| `/api/training/*` | 训练任务 CRUD / 启停 / 指标 |
| `/api/dashboard/*` | 看板总览 / 统计 / 用户管理（需 superuser） |
| `/api/profile/*` | 用户档案 + 身体指标 + 健康目标 |
| `/api/camera/*` | 摄像头图片管理 |

---

## 🧠 YOLO 模型训练

模型基于 [UECFOOD-256](http://foodcam.mobi/dataset256.html) 数据集训练，详细流程见 [`backend/train_yolo.py`](backend/train_yolo.py)。

**训练配置：**
- 基础模型：`yolo11s.pt` (COCO 预训练)
- 超参：100 epochs，batch=32，img_size=640，patience=15
- 自动 batch 降级（OOM 时 32 → 24 → 16 → 12 → 8 → 4 → 2）
- AMP 混合精度 + RAM 缓存 + Mosaic 增强

**产出：** `data/models/yolo11_food_best.pt` (26.5 MB)，mAP@50 ≈ 72.7%

---

## 🔍 三层检测管线

```text
YOLO11s (conf=0.1)
  ├── conf ≥ 0.25 → 直接采用
  └── conf < 0.25 → low_confidence=True → vision_verify_food (Qwen3-VL)
```

---

## 🗄️ 数据库模型

13 张 ORM 表（见 [`app/entity/db_models.py`](backend/app/entity/db_models.py)）：

| 表名 | 用途 |
|------|------|
| `users` / `roles` / `permissions` / `user_roles` / `role_permissions` | RBAC 用户权限体系 |
| `chat_sessions` / `chat_messages` | AI 对话会话与消息持久化 |
| `detection_scenes` / `detection_tasks` | YOLO 检测场景与每次检测记录 |
| `training_tasks` | 模型训练任务配置与状态 |
| `food_nutrition` | 食物营养数据（每 100g 热量 / 蛋白质 / 脂肪 / 碳水 / 纤维） |
| `body_profiles` / `goal_profiles` | 用户身体指标与健康目标 |

表通过 `Base.metadata.create_all()` 自动建表（Alembic 待启用）。

---

## 🖥️ 前端

前端为独立仓库：[xjtuyy/NutriMind-Agent-Frontend](https://github.com/xjtuyy/NutriMind-Agent-Frontend) （现已合并到该仓库）

- **技术栈**：Vue 3 + Vite + Vue Router + Pinia + Axios + Element Plus
- **双工作区**：用户端（AI 教练 / 拍照识别 / 知识库 / 个人档案）+ 管理端（看板 / 用户管理 / 检测监控 / 训练管理）
- **启动**（需 Node.js 20+，后端运行于 `http://localhost:9999`）：

```bash
npm install
npm run dev        # http://localhost:3000，/api 代理到 9999
```

---


## 📄 License

本项目仅供学习与内部研发使用。
