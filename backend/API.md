# NutriMind-Agent 后端 API 文档

> **Base URL:** `http://localhost:9999`  
> **Swagger:** [http://localhost:9999/docs](http://localhost:9999/docs)  
> **ReDoc:** [http://localhost:9999/redoc](http://localhost:9999/redoc)

---

## 目录

- [1. 健康检查](#1-健康检查)
- [2. 认证](#2-认证)
- [3. 知识库](#3-知识库)
- [4. 摄像头](#4-摄像头)
- [5. 数据看板](#5-数据看板)
- [6. 通用说明](#6-通用说明)

---

## 1. 健康检查

### `GET /api/health`

服务存活检查，无需认证。

**响应示例：**

```json
{
  "status": "ok",
  "message": "VisAgent API is running"
}
```

---

## 2. 认证

### 2.1 用户注册

```http
POST /api/auth/register
```

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| `username` | string | ✅ | 用户名，3-50 字符 |
| `email` | string | ✅ | 邮箱，合法格式 |
| `password` | string | ✅ | 密码，至少 6 位 |

**请求示例：**

```json
{
  "username": "zhangsan",
  "email": "zhangsan@example.com",
  "password": "mypassword123"
}
```

**成功响应 `201`：**

```json
{
  "id": 18,
  "username": "zhangsan",
  "email": "zhangsan@example.com",
  "phone": null,
  "avatar": null,
  "is_active": true,
  "is_superuser": false,
  "roles": [],
  "last_login_at": null,
  "created_at": "2026-07-15T11:14:17.872587"
}
```

**错误响应：**

| 状态码 | 说明 |
|:--:|------|
| `400` | 用户名已存在 / 邮箱已被注册 / 字段校验失败 |
| `500` | 服务器内部错误 |

---

### 2.2 用户登录

```http
POST /api/auth/login
```

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| `username` | string | ✅ | 用户名 |
| `password` | string | ✅ | 密码 |

**请求示例：**

```json
{
  "username": "zhangsan",
  "password": "mypassword123"
}
```

**成功响应 `200`：**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": 18,
    "username": "zhangsan",
    "email": "zhangsan@example.com",
    "avatar": null,
    "roles": []
  }
}
```

> 同时设置 HttpOnly Cookie `access_token`，有效期 30 分钟。

**错误响应：**

| 状态码 | 说明 |
|:--:|------|
| `401` | 用户名或密码错误 |
| `403` | 账户已被禁用 |
| `500` | 服务器内部错误 |

---

### 2.3 获取当前用户信息

```http
GET /api/auth/me
Authorization: Bearer {access_token}
```

**成功响应 `200`：**

```json
{
  "id": 18,
  "username": "zhangsan",
  "email": "zhangsan@example.com",
  "phone": null,
  "avatar": null,
  "is_active": true,
  "is_superuser": false,
  "roles": [],
  "last_login_at": "2026-07-15T11:14:20.895556",
  "created_at": "2026-07-15T11:14:17.872587"
}
```

**错误响应：**

| 状态码 | 说明 |
|:--:|------|
| `401` | 未提供 Token / Token 无效或过期 |
| `500` | 服务器内部错误 |

---

### 2.4 修改密码

```http
POST /api/auth/change-password
Authorization: Bearer {access_token}
```

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| `old_password` | string | ✅ | 旧密码 |
| `new_password` | string | ✅ | 新密码，至少 6 位 |

**请求示例：**

```json
{
  "old_password": "mypassword123",
  "new_password": "newpassword456"
}
```

**成功响应 `200`：**

```json
{
  "message": "密码修改成功"
}
```

**错误响应：**

| 状态码 | 说明 |
|:--:|------|
| `400` | 旧密码错误 |
| `401` | 未认证 |
| `500` | 服务器内部错误 |

---

### 2.5 登出

```http
POST /api/auth/logout
```

> 无需认证。仅通知浏览器清除 `access_token` Cookie。

**成功响应 `200`：**

```json
{
  "message": "已登出"
}
```

---

## 3. 知识库

> 所有接口需要认证：`Authorization: Bearer {access_token}`

### 3.1 上传文档/图片

```http
POST /api/knowledge/upload
Content-Type: multipart/form-data
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| `file` | file | ✅ | 文档或图片文件 |

**支持格式：**

| 类型 | 扩展名 | 处理方式 |
|------|--------|----------|
| 文本 | `.txt` `.md` | 直接分块 → 向量化 |
| PDF | `.pdf` | 解析文本 → 分块 → 向量化 |
| 图片 | `.png` `.jpg` `.jpeg` `.gif` `.bmp` `.webp` | 多模态 OCR 描述 → 向量化 |

> 图片通过 **Qwen3-VL-8B-Instruct** 多模态模型提取描述文本，再向量化存储。

**请求示例（cURL）：**

```bash
curl -X POST http://localhost:9999/api/knowledge/upload \
  -H "Authorization: Bearer eyJhbG..." \
  -F "file=@screenshot.png"
```

**成功响应 `200`：**

```json
{
  "code": 200,
  "message": "文档上传成功",
  "data": {
    "filename": "screenshot.png",
    "chunks_count": 2
  }
}
```

**错误响应：**

| 状态码 | 说明 |
|:--:|------|
| `400` | 不支持的文件类型 / 文档处理失败 |
| `401` | 未认证 |
| `500` | 服务器内部错误 |

---

### 3.2 语义检索

```http
GET /api/knowledge/search?query={关键词}&k={数量}
```

**查询参数：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|:--:|------|------|
| `query` | string | ✅ | - | 检索关键词 |
| `k` | int | ❌ | `5` | 返回结果数量 |

**请求示例：**

```bash
curl "http://localhost:9999/api/knowledge/search?query=营养学&k=3" \
  -H "Authorization: Bearer eyJhbG..."
```

**成功响应 `200`：**

```json
{
  "code": 200,
  "data": {
    "query": "营养学",
    "results": [
      {
        "content": "营养学是研究食物与健康关系的科学...",
        "metadata": {
          "source": "/tmp/xxx.txt",
          "file_name": "nutrition.txt"
        },
        "score": 0.9521
      }
    ],
    "total": 1
  }
}
```

| 字段 | 说明 |
|------|------|
| `content` | 匹配的文本内容 |
| `metadata.source` | 来源文件路径 |
| `metadata.file_name` | 原始文件名 |
| `metadata.type` | 文档类型（`image` / 文本） |
| `score` | 语义相似度（越高越相关） |

**错误响应：**

| 状态码 | 说明 |
|:--:|------|
| `400` | 查询内容为空 |
| `401` | 未认证 |
| `500` | 检索失败 |

---

### 3.3 删除文档

```http
DELETE /api/knowledge/?source={来源路径}
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| `source` | string | ✅ | 文档来源路径（metadata.source） |

**成功响应 `200`：**

```json
{
  "code": 200,
  "message": "文档删除成功"
}
```

**错误响应：**

| 状态码 | 说明 |
|:--:|------|
| `400` | 文档来源为空 |
| `404` | 未找到指定文档 |
| `401` | 未认证 |
| `500` | 删除失败 |

---

### 3.4 知识库统计

```http
GET /api/knowledge/stats
```

**成功响应 `200`：**

```json
{
  "code": 200,
  "data": {
    "total_chunks": 7,
    "sources": [
      { "source": "/tmp/xxx.png", "count": 2 },
      { "source": "/tmp/yyy.txt", "count": 1 }
    ]
  }
}
```

| 字段 | 说明 |
|------|------|
| `total_chunks` | 知识库总向量块数 |
| `sources` | 各来源文件及其块数 |

---

## 5. 数据看板

> 所有接口需要认证：`Authorization: Bearer {access_token}`

### 5.1 总览

```http
GET /api/dashboard/overview
```

**成功响应 `200`：**

```json
{
  "code": 200,
  "data": {
    "total_users": 19,
    "active_users": 19,
    "total_detection_scenes": 0,
    "total_detection_tasks": 0,
    "total_training_tasks": 0,
    "total_food_items": 0
  }
}
```

| 字段 | 说明 |
|------|------|
| `total_users` | 用户总数 |
| `active_users` | 活跃用户数 |
| `total_detection_scenes` | 检测场景数 |
| `total_detection_tasks` | 检测任务总数 |
| `total_training_tasks` | 训练任务总数 |
| `total_food_items` | 食物营养条目数 |

### 5.2 检测统计

```http
GET /api/dashboard/detection
```

| 字段 | 说明 |
|------|------|
| `total` | 检测任务总数 |
| `completed` / `failed` / `pending` / `processing` | 各状态任务数 |
| `total_objects_detected` | 累计检测目标数 |
| `avg_inference_time` | 平均推理耗时（秒） |

### 5.3 训练统计

```http
GET /api/dashboard/training
```

| 字段 | 说明 |
|------|------|
| `total` | 训练任务总数 |
| `completed` / `failed` / `running` / `pending` / `paused` | 各状态任务数 |

### 5.4 用户统计

```http
GET /api/dashboard/users
```

| 字段 | 说明 |
|------|------|
| `total` | 用户总数 |
| `active` | 活跃用户数 |
| `superusers` | 管理员数 |
| `new_today` | 今日新增 |

### 5.5 完整看板

```http
GET /api/dashboard/stats
```

聚合以上所有数据，返回 `overview + detection + training + users`。

### 5.6 检测状态分布

```http
GET /api/dashboard/detection/status-distribution
```

返回各状态 `[{status, count}, ...]`。

### 5.7 训练状态分布

```http
GET /api/dashboard/training/status-distribution
```

返回各状态 `[{status, count}, ...]`。

---

## 6. 通用说明

### 认证方式

登录成功后，使用以下任一方式传递 Token：

1. **Header（推荐）：** `Authorization: Bearer {access_token}`
2. **Cookie：** 浏览器自动携带 `access_token` HttpOnly Cookie

### JWT 配置

| 配置项 | 值 |
|--------|-----|
| 签名算法 | HS256 |
| 访问令牌有效期 | 30 分钟 |
| 刷新令牌有效期 | 7 天 |

### 错误响应格式

所有错误统一格式：

```json
{
  "detail": "错误描述信息"
}
```

### 技术栈

```
框架:    FastAPI + Uvicorn
认证:    JWT (python-jose) + bcrypt (passlib)
数据库:  PostgreSQL + PGVector (向量存储)
OCR:     Qwen3-VL-8B-Instruct (多模态)
Embedding: Qwen3-Embedding-8B
LLM:     Qwen3.6-35B-A3B
```

---

## 4. 摄像头

> 所有接口需要认证：`Authorization: Bearer {access_token}`

### 4.1 拍照上传

```http
POST /api/camera/capture
Content-Type: multipart/form-data
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| `file` | file | ✅ | 图片文件（png/jpg/gif/bmp/webp） |

**请求示例（cURL）：**

```bash
curl -X POST http://localhost:9999/api/camera/capture \
  -H "Authorization: Bearer eyJhbG..." \
  -F "file=@photo.png"
```

**成功响应 `200`：**

```json
{
  "code": 200,
  "message": "图片上传成功",
  "data": {
    "id": "a2e9367c537446409cdb474b01873a92.png",
    "original_name": "photo.png",
    "size": 69,
    "user_id": 19,
    "created_at": "2026-07-15T14:59:53"
  }
}
```

### 4.2 拍照历史

```http
GET /api/camera/list?page=1&page_size=20
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|:--:|------|------|
| `page` | int | ❌ | `1` | 页码 |
| `page_size` | int | ❌ | `20` | 每页数量（1-100） |

**成功响应 `200`：**

```json
{
  "code": 200,
  "data": {
    "items": [
      { "id": "xxx.png", "filename": "xxx.png", "size": 69, "created_at": "..." }
    ],
    "total": 2,
    "page": 1,
    "page_size": 20
  }
}
```

### 4.3 查看图片

```http
GET /api/camera/view/{image_id}
```

直接返回图片文件流。

### 4.4 删除图片

```http
DELETE /api/camera/{image_id}
```

**成功响应 `200`：**

```json
{ "code": 200, "message": "图片已删除" }
```

---

### 当前部署状态

| 模块 | 端点 | 状态 |
|------|------|:--:|
| 健康检查 | `GET /api/health` | ✅ 已部署 |
| 认证 | 注册/登录/个人信息/修改密码/登出 | ✅ 已部署 |
| 知识库 | 上传/检索/删除/统计 | ✅ 已部署 |
| 摄像头 | 拍照/列表/查看/删除 | ✅ 已部署（按用户隔离） |
| 数据看板 | 总览/检测/训练/用户/状态分布 | ✅ 已部署 |
| 目标检测 | — | ⏳ Service 已就绪，API 未接线 |
| 模型训练 | — | ⏳ Service 已就绪，API 未接线 |
| 智能对话 | — | ⏳ Service 已就绪，API 未接线 |

### 认证策略

| 项目 | 当前实现 |
|------|------|
| 浏览器认证 | **Header + Cookie 双通道** 均可 |
| Refresh Token | ❌ 配置存在但无接口 |
| 管理员判断 | `is_superuser` 字段 + `roles` 包含 `admin` |
| 登出 | 幂等，无需认证，清除 Cookie |

### 安全与隔离

| 项目 | 状态 |
|------|:--:|
| Camera 用户隔离 | ✅ 文件名内置 user_id，列表/查看/删除均校验 |
| Camera 路径暴露 | ✅ 不返回服务器绝对路径 |
| 知识库用户隔离 | ❌ 当前为全局共享 |
| Dashboard 权限 | ❌ 当前仅需登录，未限制管理员 |
| DEBUG 模式 | ⚠️ 默认 `true`，生产应设为 `false` |
