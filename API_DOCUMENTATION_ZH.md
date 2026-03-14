# 量化比赛模块 API 接口文档

本文档定义了量化比赛模块的 REST API 端点、请求参数和响应结构，基于"会议日程草案"中商定的架构。

> **最后更新:** 2026-03-05

## 实现状态

| 章节 | 范围 | 状态 | 阶段 |
| :--- | :--- | :--- | :--- |
| 2. 身份验证 | Amazon Cognito Auth（客户端） | **已完成** | 第一阶段 |
| 2.4 用户资料 | GET /me、PATCH /me | **已完成** | 第一阶段 |
| 2.5 管理员 | 用户 CRUD、角色列表 | **已完成** | 第七阶段 |
| 3. 系统端点 | 健康检查、版本 | **已完成**（健康检查返回硬编码值） | 第一阶段 |
| 4.1–4.5 策略 CRUD | 创建、列表、详情、更新、删除 | **已完成** | 第一阶段 |
| 4.6–4.7 策略生命周期 | 启动、停止（仅 DB 状态转换；ME 生命周期 RPC 待实现） | **已完成** | 第二阶段 |
| 4.8 策略状态 | 运行状态 + 运行时长 | **已完成** | 第一阶段 |
| 4.9 策略表现 | ROI、夏普比率、最大回撤、胜率、盈亏比 | **已完成** | 第四阶段 |
| 4.10–4.12 策略分析 | 每日收益、资产曲线、资产配置 | **已完成** | 第四阶段 |
| 5. 持仓与成交 | 当前/历史持仓、成交记录 | **已完成** | 第四阶段 |
| 6.1–6.3 市场数据 | 盘口、K 线、交易对信息 | **已完成** | 第三阶段 |
| 6.4 交易对配置 | 可用交易对 + 精度配置 + 元数据 | **已完成** | 第三阶段 |
| 7. WebSocket | 实时推送（策略 + 市场频道，原生 ping/pong） | **已完成** | 第五阶段 |
| 8. 内部协议 | gRPC + Redis pub/sub | **已完成** | 第二阶段 |
| 频率限制 | 按类别的请求节流 | **未开始** | 待定 |

**REST API: 29/29 个端点已实现并测试（156 个集成测试）。**

---

## 1. 通用约定

*   **基础 URL:** `/v1`
*   **内容类型:** `application/json`
*   **身份验证:** 所有端点均需要在 `Authorization` 请求头中携带有效的 Cognito ID 令牌：`Authorization: Bearer <cognito_id_token>`，**以下公开端点除外：**
    *   `GET /health`
    *   `GET /version`
    *   `GET /symbols`
*   **用户隔离:** 策略、持仓和成交记录以用户为维度隔离 — 每个用户只能访问自己的数据。访问其他用户的资源将返回 `404 Not Found`（防止泄露存在信息）。
*   **时间格式:** Unix 毫秒时间戳（例如：`1707667200000`）。唯一的例外是 `/strategies/{strategyId}/daily-returns` 中的 `date` 字段，它使用 ISO 8601 日期字符串（`"YYYY-MM-DD"`），因为每日粒度不需要完整的时间戳。
*   **策略范围:** API 支持**多策略**运行。所有策略相关端点均需要 `{strategyId}` 路径参数（例如：`/strategies/{strategyId}/status`）。策略遵循定义的生命周期：`Created → Running → Stopped`，其中 `Error` 和 `Deleted` 分别为异常态和软删除态。
*   **响应包装:** 所有成功的响应都包装在一个标准的信封结构中。

```json
{
  "code": 0,           // 0 = 成功, 非零 = 错误代码
  "message": "success", // 可读的状态或错误信息
  "data": { ... },      // 实际负载数据
  "timestamp": 1707667200000
}
```

*   **频率限制（已规划，尚未实现）:** API 请求将按客户端 IP（或开启认证后的每个用户）进行频率限制。限制信息将在响应头中返回：
    *   `X-RateLimit-Limit`: 每个窗口期的最大请求数。
    *   `X-RateLimit-Remaining`: 当前窗口期内的剩余请求数。
    *   `X-RateLimit-Reset`: 窗口期重置的 Unix 时间戳（毫秒）。
    *   超出限制时，API 返回 HTTP `429 Too Many Requests`。

    | 端点类别 | 频率限制 |
    | :--- | :--- |
    | 市场数据 (`/market/*`) | 60 次请求/秒 |
    | 策略与持仓 | 30 次请求/秒 |
    | 身份验证 (`/auth/*`) | 10 次请求/秒 |
    | 系统 (`/health`, `/version`) | 10 次请求/秒 |

### 1.1 错误代码

所有错误均使用带有非零 `code` 的标准响应信封。HTTP 状态码按常规使用（400, 401, 404, 429, 500, 503）。

| 代码 | HTTP 状态 | 含义 |
| :--- | :--- | :--- |
| 0 | 200 | 成功 |
| 1001 | 400 | 参数无效 — 缺少或格式错误的请求参数 |
| 1002 | 400 | 交易对无效 — 不支持所请求的交易对 |
| 1003 | 400 | 时间范围无效 — `startTime` >= `endTime` 或超出范围 |
| 2001 | 409 | 策略未运行 — 操作需要策略处于运行状态 |
| 2002 | 409 | 策略已运行 — 无法启动已激活的策略 |
| 2003 | 409 | 无效状态转换 — 无法修改或删除运行中的策略 |
| 3001 | 401 | 未授权 — 缺少、无效或过期的 Cognito ID 令牌 |
| 3002 | 403 | 禁止访问 — 令牌有效但权限不足（RBAC） |
| 4001 | 404 | 资源未找到 |
| 5001 | 500 | 内部服务器错误 |
| 5002 | 503 | 匹配引擎不可用 |
| 9001 | 429 | 超出频率限制 |

---

## 2. 身份验证

身份验证完全由客户端的 **Amazon Cognito** 处理。后端不暴露任何认证端点（`/auth/*`）。后端在每个受保护的请求上**验证 Cognito ID 令牌**，并自动创建本地用户记录。

**流程：**
1. 用户通过 Cognito Hosted UI 或前端 SDK 注册/登录（邮箱+密码、社交登录等）
2. 前端从 Cognito 获取 ID 令牌
3. 前端在 `Authorization: Bearer <cognito_id_token>` 请求头中发送令牌
4. 后端通过 PyJWT + Cognito JWKS 公钥本地验证令牌（无需 AWS 凭证）
5. 首次验证成功时，后端自动创建本地 `User` 记录（或通过邮箱关联现有记录）

*   **RBAC（基于角色的访问控制）：** 用户通过 `role_id` 外键关联 `roles` 表（3 个默认角色：`admin`、`moderator`、`user`）。每个角色拥有一组权限字符串（如 `user:manage`、`role:manage`）。端点通过 `require_permission("resource:action")` 或 `require_role(["admin"])` 依赖进行守卫。`user.role` 属性返回角色名称字符串以保持向后兼容。

### 2.1 用户资料

#### 2.1.1 获取我的资料

返回已认证用户的个人资料信息。

*   **端点:** `GET /users/me`
*   **身份验证:** 需要（Bearer Cognito ID 令牌）。
*   **响应数据 (200 OK):**
    ```json
    {
      "id": "a1b2c3d4-...",
      "username": "myuser",
      "email": "user@example.com",
      "role": "user",
      "role_id": 3,
      "is_active": true,
      "created_at": 1707667200000,
      "updated_at": 1707667200000,
      "display_name": "我的显示名称",
      "avatar_url": "https://example.com/avatar.png",
      "bio": "量化交易员和开发者",
      "country": "CN",
      "region": "上海",
      "city": "上海",
      "institution_name": "复旦大学",
      "department": "计算机科学",
      "graduation_year": 2020,
      "participant_type": "student",
      "social_links": "{\"github\": \"https://github.com/user\"}",
      "is_profile_public": true
    }
    ```
    | 字段 | 类型 | 描述 |
    | :--- | :--- | :--- |
    | `id` | string | 用户 UUID |
    | `username` | string | 登录用户名 |
    | `email` | string | 邮箱地址 |
    | `role` | string | 角色名称（`"user"`、`"moderator"` 或 `"admin"`） |
    | `role_id` | integer | `roles` 表外键 (1=admin, 2=moderator, 3=user) |
    | `is_active` | boolean | 账户激活状态 |
    | `created_at` | integer | 账户创建时间戳（Unix 毫秒） |
    | `updated_at` | integer | 最后资料更新时间戳（Unix 毫秒） |
    | `display_name` | string \| null | 显示名称（与登录用户名分开） |
    | `avatar_url` | string \| null | 头像 URL |
    | `bio` | string \| null | 个人简介（最多 280 字符） |
    | `country` | string \| null | ISO alpha-2 国家代码（如 `"CN"`、`"US"`） |
    | `region` | string \| null | 省/州 |
    | `city` | string \| null | 城市 |
    | `institution_name` | string \| null | 机构名称 |
    | `department` | string \| null | 院系/专业 |
    | `graduation_year` | integer \| null | 毕业年份 |
    | `participant_type` | string | `"student"` \| `"professional"` \| `"independent"`（默认） |
    | `social_links` | string \| null | 社交媒体链接 JSON 字符串 |
    | `is_profile_public` | boolean | 个人资料是否公开可见（默认 `true`） |

#### 2.1.2 更新我的资料

更新已认证用户的可修改资料字段。

*   **端点:** `PATCH /users/me`
*   **身份验证:** 需要（Bearer Cognito ID 令牌）。
*   **请求体:**
    ```json
    {
      "username": "newusername",
      "display_name": "新显示名称",
      "bio": "更新的简介",
      "country": "US",
      "participant_type": "professional"
    }
    ```
    | 字段 | 类型 | 必填 | 描述 |
    | :--- | :--- | :--- | :--- |
    | `username` | string | 否 | 新用户名（3–50 字符，必须唯一） |
    | `display_name` | string | 否 | 显示名称（最多 64 字符） |
    | `avatar_url` | string | 否 | 头像 URL（最多 512 字符） |
    | `bio` | string | 否 | 个人简介（最多 280 字符） |
    | `country` | string | 否 | ISO alpha-2 国家代码（2 字符，自动转为大写） |
    | `region` | string | 否 | 省/州（最多 64 字符） |
    | `city` | string | 否 | 城市（最多 64 字符） |
    | `institution_name` | string | 否 | 机构名称（最多 128 字符） |
    | `department` | string | 否 | 院系/专业（最多 128 字符） |
    | `graduation_year` | integer | 否 | 毕业年份 |
    | `participant_type` | string | 否 | `"student"` \| `"professional"` \| `"independent"` |
    | `social_links` | string | 否 | 社交媒体链接 JSON 字符串 |
    | `is_profile_public` | boolean | 否 | 个人资料是否公开可见 |

*   **响应数据 (200 OK):** 与获取资料接口相同的 `UserProfileResponse` 结构。

*   **错误响应:**
    | 代码 | HTTP | 条件 |
    | :--- | :--- | :--- |
    | 2002 | 409 | 用户名已被占用 |
    | 1001 | 400 | 无效的 `participant_type` 或 `country` 代码 |

### 配置

| 环境变量 | 描述 |
| :--- | :--- |
| `COGNITO_USER_POOL_ID` | Cognito 用户池 ID（例如 `ap-southeast-1_XXXXXXXXX`） |
| `COGNITO_CLIENT_ID` | Cognito 应用客户端 ID |
| `COGNITO_REGION` | Cognito 用户池所在 AWS 区域（默认 `ap-southeast-1`） |

### 2.5 管理员端点

用于用户管理和角色/权限查看的管理员端点。所有端点均需要特定权限。

#### 2.5.1 用户列表

*   **端点:** `GET /admin/users`
*   **身份验证:** 需要。需要 `user:manage` 权限（admin 角色）。
*   **查询参数：**

    | 参数 | 类型 | 默认值 | 描述 |
    | :--- | :--- | :--- | :--- |
    | `page` | integer | 1 | 页码（>= 1） |
    | `size` | integer | 20 | 每页大小（1–100） |
    | `role_id` | integer | — | 按角色 ID 过滤 |
    | `is_active` | boolean | — | 按激活状态过滤 |
    | `search` | string | — | 搜索用户名或邮箱（模糊匹配） |

*   **响应数据 (200 OK):** `PaginatedData[UserProfileResponse]`

#### 2.5.2 获取用户

*   **端点:** `GET /admin/users/{user_id}`
*   **身份验证:** 需要。需要 `user:manage` 权限。
*   **响应数据 (200 OK):** `UserProfileResponse`
*   **错误:** 用户不存在返回 `404`。

#### 2.5.3 更新用户

*   **端点:** `PATCH /admin/users/{user_id}`
*   **身份验证:** 需要。需要 `user:manage` 权限。
*   **请求体：**

    | 字段 | 类型 | 描述 |
    | :--- | :--- | :--- |
    | `role_id` | integer? | 新角色 ID |
    | `is_active` | boolean? | 激活状态 |
    | `username` | string? | 新用户名 |
    | *(资料字段)* | — | 与 PATCH /users/me 相同 |

*   **安全检查：**
    *   不能更改自己的角色 → `400`
    *   不能停用自己 → `400`
    *   无效的 `role_id` → `400`

*   **响应数据 (200 OK):** `UserProfileResponse`

#### 2.5.4 角色列表

*   **端点:** `GET /admin/roles`
*   **身份验证:** 需要。需要 `role:manage` 权限（admin 角色）。
*   **响应数据 (200 OK):** `RoleDetailResponse` 数组：
    ```json
    [
      {
        "id": 1,
        "name": "admin",
        "description": "完整系统访问权限",
        "level": 100,
        "permissions": ["user:manage", "role:manage", "system:manage", ...]
      }
    ]
    ```

#### 2.5.5 获取角色权限

*   **端点:** `GET /admin/roles/{role_id}/permissions`
*   **身份验证:** 需要。需要 `role:manage` 权限。
*   **响应数据 (200 OK):** 权限字符串数组。
*   **错误:** 角色不存在返回 `404`。

---

## 3. 系统端点

### 3.1 健康检查
用于部署和监控的基础可用性探测。

*   **端点:** `GET /health`
*   **身份验证:** 不需要。
*   **响应数据:**
    ```json
    {
      "status": "ok",            // "ok" | "degraded" | "down"
      "matchingEngine": "ok",    // 匹配引擎连接状态
      "database": "ok",          // 数据库连接状态
      "redis": "ok"              // Redis 连接状态
    }
    ```

> **实现说明:** `matchingEngine` 基于 gRPC 健康检查结果返回（`ok`/`down`），并通过 `matchingEngineDetail` 提供细节。`database` 与 `redis` 目前仍为占位 `"ok"`，后续会补充真实 ping 检查。

### 3.2 版本信息
返回 API 版本信息，用于前端兼容性检查。

*   **端点:** `GET /version`
*   **身份验证:** 不需要。
*   **响应数据:**
    ```json
    {
      "apiVersion": "1.0.0",
      "buildHash": "a1b2c3d"
    }
    ```

---

## 4. 策略端点

所有策略端点使用 `/strategies` 前缀，需要身份验证（Bearer Cognito ID 令牌），通过 `{strategyId}` 路径参数支持**多策略**操作。

### 策略生命周期

策略遵循以下状态机转换：

```
Created ──► Running ──► Stopped ──► Running (重启)
   │            │           │
   ▼            ▼           ▼
 Deleted      Error      Deleted
                │
                ▼
              Running (重试)
```

*   **状态值:** `"Created"` | `"Running"` | `"Stopped"` | `"Error"` | `"Deleted"`（策略记录软删除保留用于审计；所有子记录硬删除）
*   **约束:** 运行中的策略不能被修改或删除 — 必须先停止。

### 4.1 创建策略
创建一个新的交易策略，初始状态为 `Created`。

*   **端点:** `POST /strategies`
*   **请求体:**
    ```json
    {
      "name": "BTC 动量策略 Alpha",
      "description": "BTCUSDT 趋势跟踪策略",
      "code": "int main() { ... }",
      "language": "c++",
      "initialBalance": 10000.0
    }
    ```
    | 字段 | 类型 | 必填 | 描述 |
    | :--- | :--- | :--- | :--- |
    | `name` | string | 是 | 策略名称（1–255 字符） |
    | `description` | string | 否 | 可选描述 |
    | `code` | string | 是 | 策略源代码（最大 100 KB）。空字节和不可打印控制字符会被自动去除。 |
    | `language` | string | 否 | 编程语言。当前仅支持 `"c++"`。默认值: `"c++"` |
    | `initialBalance` | number | 否 | 初始资金 |

*   **响应数据 (201 Created):**
    ```json
    {
      "id": "a1b2c3d4-...",
      "name": "BTC 动量策略 Alpha",
      "description": "BTCUSDT 趋势跟踪策略",
      "status": "Created",
      "code": "int main() { ... }",
      "language": "c++",
      "version": 1,
      "initialBalance": 10000.0,
      "totalEquity": null,
      "startedAt": null,
      "stoppedAt": null,
      "createdAt": 1707667200000,
      "updatedAt": 1707667200000
    }
    ```

### 4.2 获取策略列表
检索所有策略的分页列表（不含软删除的策略）。

*   **端点:** `GET /strategies`
*   **查询参数:**
    *   `page` (可选): 页码。默认值: `1`。
    *   `size` (可选): 每页数量。默认值: `20`。最大值: `100`。
    *   `status` (可选): 按状态过滤（`Created`, `Running`, `Stopped`, `Error`）。
*   **响应数据:**
    ```json
    {
      "list": [
        {
          "id": "a1b2c3d4-...",
          "name": "BTC 动量策略 Alpha",
          "description": "趋势跟踪策略",
          "status": "Running",
          "language": "c++",
          "version": 1,
          "initialBalance": 10000.0,
          "totalEquity": 10350.50,
          "createdAt": 1707667200000,
          "updatedAt": 1707670800000
        }
      ],
      "total": 5,
      "page": 1,
      "size": 20
    }
    ```

### 4.3 获取策略详情
检索单个策略的完整详情。

*   **端点:** `GET /strategies/{strategyId}`
*   **路径参数:**
    *   `strategyId`: 策略 UUID。
*   **响应数据:** 与创建策略的响应结构相同（见 4.1 节）。

### 4.4 更新策略
更新策略的可变字段。仅当状态为 `Created` 或 `Stopped` 时允许（`Running` 状态下不可修改）。更新 `code` 字段会自动递增 `version` 版本号并归档上一版本。

*   **端点:** `PUT /strategies/{strategyId}`
*   **请求体（部分更新 — 所有字段均为可选）:**
    ```json
    {
      "name": "BTC 动量策略 Alpha v2",
      "code": "int main() { /* v2 */ }",
      "description": "更新后的趋势跟踪策略",
      "language": "c++",
      "initialBalance": 20000.0
    }
    ```
*   **响应数据:** 完整的策略详情（与 4.1 节结构相同）。
*   **错误:** 如果策略当前为 `Running` 状态，返回 `409 Conflict`。

### 4.5 删除策略
软删除策略并**硬删除所有子记录**（成交记录、持仓、权益快照、每日指标、策略版本）。策略记录本身以 `status = "Deleted"` 保留用于审计追踪，但所有关联数据将从数据库中永久移除。

*   **端点:** `DELETE /strategies/{strategyId}`
*   **响应数据:** `null`（附带 `"message": "Strategy deleted"`）。
*   **错误:** 如果策略当前为 `Running` 状态，返回 `409 Conflict`。
*   **副作用:**
    *   该策略下的所有成交记录、持仓、权益快照、每日指标和策略版本将被永久删除。
    *   该策略的内存快照缓冲区将被丢弃。
    *   该策略的绩效缓存将被失效。

### 4.6 启动策略
将策略从 `Created`、`Stopped` 或 `Error` 状态转换为 `Running`。首次启动时，`totalEquity` 将从 `initialBalance` 初始化。

> **注意:** 当前为纯 DB 状态转换。ME 的策略生命周期 RPC（启动/停止）尚未由匹配引擎实现。待实现后，此端点将同时调用 ME 开始执行策略。

*   **端点:** `POST /strategies/{strategyId}/start`
*   **响应数据:** 包含更新后状态的完整策略详情。
    ```json
    {
      "id": "a1b2c3d4-...",
      "status": "Running",
      "startedAt": 1707670800000,
      "totalEquity": 10000.0,
      ...
    }
    ```
*   **错误:** 如果策略已处于 `Running` 状态，返回 `409 Conflict`。

### 4.7 停止策略
将策略从 `Running` 状态转换为 `Stopped`。

> **注意:** 当前为纯 DB 状态转换。ME 的策略生命周期 RPC（启动/停止）尚未由匹配引擎实现。待实现后，此端点将同时调用 ME 停止策略执行。

*   **端点:** `POST /strategies/{strategyId}/stop`
*   **响应数据:** 包含更新后状态的完整策略详情。
    ```json
    {
      "id": "a1b2c3d4-...",
      "status": "Stopped",
      "stoppedAt": 1707674400000,
      ...
    }
    ```
*   **错误:** 如果策略不在 `Running` 状态，返回 `409 Conflict`。

### 4.8 获取策略状态
检索策略当前的运行状态和健康状况。

*   **端点:** `GET /strategies/{strategyId}/status`
*   **响应数据:**
    ```json
    {
      "status": "Running",
      "startTime": 1707600000000,
      "uptimeSeconds": 3600
    }
    ```
    `uptimeSeconds` 仅在运行中的策略实时计算，其他状态下为 `null`。

### 4.9 获取策略表现
检索策略的关键绩效指标 (KPIs)。

*   **端点:** `GET /strategies/{strategyId}/performance`
*   **响应数据:**
    ```json
    {
      "roi": 14.5,            // 投资回报率 (%)
      "totalPnl": 1250.45,    // 总盈亏
      "sharpeRatio": 1.8,     // 年化夏普比率，sqrt(252) 缩放。数据不足 2 天时为 null。
      "maxDrawdown": 5.2,     // 峰值到谷值最大回撤 (%)。无净值数据时为 null。
      "winRate": 65.4,        // 盈利平仓数 / 总平仓数 (%)。无平仓记录时为 null。
      "profitLossRatio": 1.5  // avg(盈利 PnL) / abs(avg(亏损 PnL))。无盈利或无亏损时为 null。
    }
    ```

> **实现说明:** `roi` 和 `totalPnl` 由 `totalEquity` 与 `initialBalance` 的差值计算得出。其余四项 KPI 的计算方式：
> - **winRate / profitLossRatio:** 通过单条 SQL 聚合查询计算已平仓持仓数据（无 ORM 对象加载）。
> - **maxDrawdown / sharpeRatio:** 从**滚动 90 天窗口**的净值快照中计算。
>
> **缓存:** 每个策略的结果缓存 **30 秒 TTL**。策略停止或删除时自动失效。数据不足时相应字段返回 `null`。

### 4.10 获取每日收益
检索带有分页的历史每日表现统计数据。每日指标从净值快照实时计算（在 Python 中按日期分组，兼容 SQLite 和 PostgreSQL）。

*   **端点:** `GET /strategies/{strategyId}/daily-returns`
*   **查询参数:**
    *   `range` (可选): 时间范围过滤（`7d`, `30d`, `all`）。默认值: `30d`。
    *   `page` (可选): 页码。默认值: `1`。
    *   `size` (可选): 每页数量。默认值: `30`。最大值: `100`。
*   **响应数据:**
    ```json
    {
      "list": [
        {
          "date": "2026-02-11",
          "dailyReturn": 0.35,  // % (日间净值变化率)
          "dailyPnl": 642.18,   // 当日绝对盈亏
          "tradeCount": 12,     // 当日成交笔数
          "maxDrawdown": 0.8    // 日内峰值到谷值回撤 (%)。无回撤时为 null。
        }
      ],
      "total": 45,
      "page": 1,
      "size": 30
    }
    ```
    结果按日期从新到旧排序。

### 4.11 获取资产曲线
检索用于绘图的资产净值曲线数据点。

*   **端点:** `GET /strategies/{strategyId}/asset-curve`
*   **查询参数:**
    *   `range` (可选): 时间范围过滤（`7d`, `30d`, `all`）。默认值: `30d`。
*   **响应数据:** 每天一个数据点（每日收盘 — 每个 UTC 日期的最后一条净值快照），按时间戳升序排列。
    ```json
    [
      {
        "timestamp": 1707600000000,
        "equity": 10000.00
      },
      {
        "timestamp": 1707603600000,
        "equity": 10050.25
      }
    ]
    ```

### 4.12 获取资产配置
检索当前各交易对/币种的资产分布情况。使用实时市场价格计算各持仓价值（无市场数据时回退到入场价格）。USDT 余额 = `totalEquity - sum(持仓价值)`。

*   **端点:** `GET /strategies/{strategyId}/asset-allocation`
*   **响应数据:**
    ```json
    {
      "totalNotional": 10000.0,
      "distribution": [
        { "symbol": "USDT", "asset": "USDT", "ratio": 45.0, "value": 4500.00 },
        { "symbol": "BTCUSDT", "asset": "BTC", "ratio": 35.0, "value": 3500.00 },
        { "symbol": "ETHUSDT", "asset": "ETH", "ratio": 20.0, "value": 2000.00 }
      ]
    }
    ```
    `ratio` 为百分比（0–100）。策略无净值时返回 `{"totalNotional": 0.0, "distribution": []}`。无持仓时 `distribution` 返回单个 USDT 项（100%）。

---

## 5. 持仓与成交端点

所有持仓和成交端点需要身份验证（Bearer Cognito ID 令牌）。查询范围限定在已认证用户的策略内 — 用户无法看到其他用户的持仓或成交记录。

### 5.1 获取当前持仓
检索用户所有**运行中**策略当前持有的仓位。数据通过 **gRPC 实时从 MatchX 引擎获取**（`GetPositions` RPC）— 引擎是持仓数据的权威来源，始终返回准确的 `markPrice`（基于实时 ticker 计算）和 `unrealizedPnl`。持仓数据**不再**持久化到数据库。

*   **端点:** `GET /positions/current`
*   **身份验证:** 需要。
*   **数据来源:** gRPC `GetPositions` RPC（非数据库）。仅查询状态为 `"Running"` 的策略。如果没有运行中的策略或没有持仓，返回空数组。
*   **响应数据:** 持仓对象数组。
    ```json
    [
      {
        "symbol": "BTCUSDT",
        "side": "Long",              // "Long" | "Short"
        "leverage": 20,
        "size": 0.5,
        "entryPrice": 97500.0,
        "avgPrice": 97500.0,         // 多次入场的成本均价
        "markPrice": 98200.0,        // 来自 ME 的实时值（基于当前 ticker 计算）
        "margin": 2437.5,            // 来自 ME 的持仓保证金
        "unrealizedPnl": 350.0,      // 来自 ME 的实时值
        "unrealizedPnlPercent": 17.23, // 来自 ME 的未实现盈亏百分比
        "roe": 17.23,                // 来自 ME 的 unrealizedPnlPercent
        "marginMode": "Cross",       // "Cross" | "Isolated"（来自 ME）
        "liquidationPrice": 45000.0  // 来自 ME 的预估强平价格
      }
    ]
    ```

> **新增字段 (D-03, D-04)：**
> - `avgPrice` (`float | null`) — 多次成交的成本均价。对于 DCA 或分批建仓的持仓，可能与 `entryPrice` 不同。
> - `liquidationPrice` (`float | null`) — 来自 ME 的预估强平价格。风险管理的关键数据。
>
> **之前版本的不兼容变更：**
> - `markPrice` 和 `unrealizedPnl` 是引擎的**实时值**，不再是可能过时的数据库快照。
> - `roe` 由引擎填充（作为 `unrealizedPnlPercent`），不再返回 `null`。
> - `margin` 和 `marginMode` 从引擎响应中填充。
>
> **D-18（不兼容）:** `GET /positions/current` 已移除 `sizeUnit` 和 `openTime`。
> - `sizeUnit` 为无效字段（`PositionInfo` proto 不包含 `size_unit`）。
> - `openTime` 在 unary gRPC 路径中始终为 `null`（`PositionInfo` 不包含 `open_time`）。
> - 如需时间信息，请使用可提供事件时间戳的 `strategy/positions` 实时推送。

### 5.2 获取历史持仓
检索已平仓的历史持仓记录，支持分页。数据通过 **gRPC 实时从 MatchX 引擎获取**（`GetPositionHistory` RPC）— 引擎是已平仓记录的权威数据来源。交易对过滤在客户端执行。

*   **端点:** `GET /positions/history`
*   **身份验证:** 需要。
*   **数据来源:** gRPC `GetPositionHistory` RPC（非数据库）。仅查询状态为 `"Running"` 的策略。无运行中策略时返回空列表。
*   **查询参数:**
    *   `page`: 页码 (默认 `1`)。
    *   `size`: 每页数量 (默认 `20`, 最大 `100`)。
    *   `symbol`: 按交易对过滤 (可选，客户端过滤)。
*   **响应数据:**
    ```json
    {
      "list": [
        {
          "symbol": "ETHUSDT",
          "side": "Short",
          "leverage": 10,
          "size": 2.0,              // 平仓数量
          "maxSize": 5.0,           // 持仓生命周期内的峰值数量
          "entryPrice": 2500.0,
          "closeAvgPrice": 2480.0,  // 来自 ME 的加权平均平仓价格
          "realizedPnl": 40.0,
          "roe": 0.8,              // realizedPnl / (entryPrice * closedSize) * 100
          "totalCommission": 12.5,  // 累计交易手续费
          "totalFundingFee": 3.2,   // 累计资金费率
          "marginMode": "Cross",    // "Cross" | "Isolated"
          "openTime": 1707600000000,
          "closeTime": 1707660000000
        }
      ],
      "total": 50,
      "page": 1,
      "size": 20
    }
    ```

> **不兼容变更 (D-05)：** 此端点数据来源已从数据库切换为 gRPC。
> - `closePrice` 重命名为 `closeAvgPrice` — 来自 ME 的加权平均平仓价格（之前为数据库中的最后成交价）。
> - 移除 `sizeUnit` 和 `margin` — `ClosedPositionInfo` proto 不提供这些字段。
> - 新增 `maxSize` — 持仓生命周期内的峰值数量。
> - 新增 `totalCommission` — 持仓累计交易手续费。
> - 新增 `totalFundingFee` — 持仓累计资金费率。
> - `marginMode` 现在从 gRPC 填充（之前从数据库获取始终为 `null`）。
> - `openTime` 现在为可空类型 — 取决于 ME 是否提供该值。

### 5.3 获取成交记录
检索单个成交执行记录。数据通过 **gRPC 实时从 MatchX 引擎获取**（`GetTradeHistory` RPC）。`quoteQty` 由 `price * quantity` 计算得出。`realizedPnl` 为来自 ME 的逐笔盈亏。交易对过滤在客户端执行。

*   **端点:** `GET /trades`
*   **身份验证:** 需要。
*   **数据来源:** gRPC `GetTradeHistory` RPC（非数据库）。仅查询状态为 `"Running"` 的策略。无运行中策略时返回空列表。
*   **查询参数:**
    *   `page`: 页码 (默认 `1`)。
    *   `size`: 每页数量 (默认 `20`, 最大 `100`)。
    *   `symbol`: 按交易对过滤 (可选，客户端过滤)。
*   **响应数据:**
    ```json
    {
      "list": [
        {
          "tradeId": "100001",
          "orderId": 200001,            // 来自 ME 的原始订单 ID
          "time": 1707667200000,
          "symbol": "BTCUSDT",
          "side": "BUY",                // "BUY" | "SELL"
          "positionSide": "Long",       // "Long" | "Short"
          "action": "OPEN",             // "OPEN" | "CLOSE"（来自 ME）
          "description": "",            // 来自 ME 的可读描述
          "price": 97500.0,
          "quantity": 0.5,
          "quoteQty": 48750.0,          // 计算值: price * quantity
          "fee": 19.5,
          "realizedPnl": 0.0            // 来自 ME 的逐笔盈亏；开仓交易为 0
        }
      ],
      "total": 120,
      "page": 1,
      "size": 20
    }
    ```

> **不兼容变更 (D-01, D-06)：** 此端点数据来源已从数据库切换为 gRPC。
> - 新增 `orderId` — 关联原始订单。
> - 新增 `side` — 订单方向（`"BUY"` / `"SELL"`）。
> - 新增 `positionSide` — 持仓方向（`"Long"` / `"Short"`）。
> - `action` 值变更 — 现在为来自 ME 的 `"OPEN"` / `"CLOSE"`（之前为后端推导的 `"Open Long"` / `"Close Long"` 等）。
> - 新增 `description` — 来自 ME 的可读成交描述。
> - `realizedPnl` 现在为来自 ME 的逐笔盈亏（之前间接从关联持仓记录解析，多笔平仓时数据不准确）。

---

## 6. 市场数据端点

`/market/*` 端点通过 gRPC Unary RPC（`GetOrderBook`、`GetKlines`、`GetSymbolInfo`）直接查询 MatchX。`/symbols` 是发现/配置端点，启动时由 `ListActiveSymbols` + `GetSymbols` 加载。以上端点均无需身份验证。

> **可用性行为（更新）：** 交易对配置加载已改为**失败即报错（fail-fast）**。当 MatchX 交易对加载失败时，后端不再回退到硬编码默认交易对。若交易对配置不可用，`/symbols` 和依赖交易对校验的 `/market/*` 端点将返回 HTTP `503 Service Unavailable`，并带有明确错误信息。

### 6.1 获取盘口数据 (Order Book)
检索交易对当前的盘口快照。

*   **端点:** `GET /market/orderbook/{symbol}`
*   **路径参数:**
    *   `symbol`: 例如, `BTCUSDT`
*   **查询参数:**
    *   `depth` (可选): 每侧的价格档位数。默认值: `20`。允许值: `5`, `10`, `20`, `50`。
*   **响应数据:**
    ```json
    {
      "symbol": "BTCUSDT",
      "bids": [
        ["98100.0", "0.5"], // [价格, 数量] — 使用字符串以保证精度
        ["98099.0", "1.2"]
      ],
      "asks": [
        ["98101.0", "0.2"],
        ["98102.0", "0.8"]
      ],
      "updateId": 123456789,
      "timestamp": 1707667205123
    }
    ```

> **注意:** 盘口数据中的价格和数量值**始终为字符串**，以保持小数精度。这适用于 REST 响应、WebSocket 负载和 Redis 消息。

### 6.2 获取 K 线数据
通过 gRPC `GetKlines` 直接从 MatchX 引擎获取用于绘图的 OHLCV 数据。

*   **端点:** `GET /market/kline/{symbol}`
*   **路径参数:**
    *   `symbol`: 例如, `BTCUSDT`
*   **查询参数:**
    *   `interval` (必填): 例如, `1m`, `5m`, `15m`, `1h`, `4h`, `1d`。
    *   `size` (可选): 记录条数。默认值: `500`。最大值: `1500`。
    *   `startTime` (可选): 时间窗口开始时间 (Unix 毫秒, 闭区间)。提供时，返回从此时间戳开始的最多 `size` 条 K 线。
    *   `endTime` (可选): 时间窗口结束时间 (Unix 毫秒, 闭区间)。与 `startTime` 同时提供时，返回该窗口内最多 `size` 条 K 线。
*   **响应数据:**
    ```json
    {
      "symbol": "BTCUSDT",
      "interval": "1m",
      "klines": [
        {
          "openTime": 1707667200000,
          "open": 98000.0,
          "high": 98500.0,
          "low": 97900.0,
          "close": 98200.0,
          "volume": 150.5,
          "closeTime": 1707667259999,
          "isFinal": true
        },
        {
          "openTime": 1707667260000,
          "open": 98200.0,
          "high": 98300.0,
          "low": 98100.0,
          "close": 98150.0,
          "volume": 45.2,
          "closeTime": 1707667319999,
          "isFinal": false
        }
      ]
    }
    ```

> **不兼容变更:** 响应格式已从扁平的位置数组（`[[timestamp, open, high, low, close, volume], ...]`）变更为与 gRPC `GetKlinesResponse` 一致的结构化对象。每条 K 线现在是包含 `closeTime` 和 `isFinal` 字段的命名字典。顶层对象包含 `symbol` 和 `interval`。

### 6.3 获取交易对信息
通过 gRPC `GetSymbolInfo` 直接从 MatchX 引擎获取完整的交易对信息。

*   **端点:** `GET /market/info/{symbol}`
*   **路径参数:**
    *   `symbol`: 例如, `BTCUSDT`
*   **响应数据:**
    ```json
    {
      "symbol": "BTCUSDT",
      "contractType": 1,          // 1=USDT 保证金, 2=币本位保证金
      "baseAsset": "BTC",
      "quoteAsset": "USDT",
      "lastPrice": 98200.0,
      "markPrice": 98195.0,
      "indexPrice": 98198.0,
      "fundingRate": 0.0001,
      "nextFundingTime": 1707696000000,
      "change24h": 2.5,           // %
      "high24h": 99000.0,
      "low24h": 96500.0,
      "volume24h": 50000.0,       // 基础资产成交量
      "turnover24h": 4900000000.0, // 计价资产成交量
      "lastUpdateTime": 1707667206000
    }
    ```

> **不兼容变更:** `price` 字段已重命名为 `lastPrice`，与 gRPC 字段命名保持一致。新增字段：`contractType`、`baseAsset`、`quoteAsset`、`markPrice`、`indexPrice`、`fundingRate`、`nextFundingTime`、`high24h`、`low24h`、`turnover24h`、`lastUpdateTime`。

### 6.4 获取可用交易对
检索所有支持交易对的发现/配置数据。这是一个顶级端点（不在 `/market` 前缀下），因为它返回的是交易对配置与元数据，而不是实时行情。

*   **端点:** `GET /symbols`
*   **身份验证:** 不需要。
*   **数据来源:**
    * 交易对活跃列表来自 gRPC `ListActiveSymbols`
    * 交易对元数据来自 gRPC `GetSymbols`
    * 精度字段来自后端配置覆盖/默认值
*   **状态归一化:** MatchX 的 `status` 可能是数字或文本；后端会将其归一化为整数状态值后再返回。
*   **失败模式:** 若启动时交易对加载失败（或没有任何有效交易对），该端点返回 HTTP `503`：
    ```json
    {
      "detail": "Symbol configuration unavailable: failed to load from matching engine"
    }
    ```
*   **响应数据:**
    ```json
    [
      {
        "symbol": "BTCUSDT",
        "pricePrecision": 2,    // 价格小数位数
        "quantityPrecision": 3, // 数量小数位数
        "minQty": 0.001,
        "contractType": 1,      // 1=USDT 保证金, 2=币本位保证金
        "baseAsset": "BTC",
        "quoteAsset": "USDT",
        "status": 1             // 引擎中的交易对状态枚举值
      },
      {
        "symbol": "ETHUSDT",
        "pricePrecision": 2,
        "quantityPrecision": 4,
        "minQty": 0.01,
        "contractType": 1,
        "baseAsset": "ETH",
        "quoteAsset": "USDT",
        "status": 1
      }
    ]
    ```

> **更新（D-13）:** `GET /symbols` 现已包含来自 MatchX `GetSymbols` 的元数据字段：`contractType`、`baseAsset`、`quoteAsset`、`status`。
> **更新（2026-03-03）:** 已移除硬编码 BTC/ETH 默认回退。交易对配置异常将通过 HTTP `503` 显式返回。

---

## 7. WebSocket API

> **状态: 已实现（第五阶段）。** WebSocket 端点挂载在应用根路径 (`/`)。连接管理器、订阅/取消订阅、连接时初始快照推送、以及通过 Redis pub/sub 从 gRPC 流管道到 WebSocket 的实时数据推送均已实现。连接时的 Token 认证**尚未实现**（TODO）。

实时数据通过原生 WebSocket（JSON 帧）传输。

*   **端点:** `/`（根路径，原生 WebSocket — 非 Socket.io）
*   **协议:** 原生 WebSocket，JSON 消息帧

### 7.1 连接与身份验证

*   **连接:** 客户端建立到 `/`（根路径）的原生 WebSocket 连接。
*   **认证:** **WebSocket 尚未实现认证。** 当前所有连接无需令牌验证即可接入。实现后，服务器将验证通过查询参数传递的 Cognito ID 令牌 (`?token=<cognito_id_token>`)，并拒绝无效连接。
*   **连接确认 (ACK):** 连接成功后，服务器会在任何频道订阅或快照之前，立即发送一条确认消息：
    ```json
    {
      "type": "connected",
      "message": "Connection established"
    }
    ```
    客户端可以使用此消息来确认 WebSocket 连接已完全就绪。

### 7.2 重连与状态恢复

*   **心跳:** 已通过运行时原生 WebSocket ping/pong 实现（`uvicorn --ws-ping-interval --ws-ping-timeout`）。客户端不应发送 JSON 心跳负载（例如 `{"action":"pong"}`）。
*   **重连:** 客户端应实现自动重连与指数退避机制（推荐：1s, 2s, 4s, 8s, 最大 30s）。
*   **状态恢复:** 成功（重新）连接后，服务器自动：
    1. 发送**连接确认 (ACK)** 消息：`{"type": "connected", "message": "Connection established"}`
    2. 自动订阅策略频道（`strategy/positions`、`strategy/trades`、`strategy/account`、`strategy/orders`、`strategy/funding`）
    3. 发送 `strategy/positions`、`strategy/trades`、`strategy/account`、`strategy/orders`、`strategy/funding` 的完整**快照**，类型为 `"type": "snapshot"`

    客户端收到快照后必须完全替换本地状态。市场数据频道（`ticker:{symbol}`、`orderbook:{symbol}`、`kline:{symbol}`）需要客户端**显式订阅**；订阅后服务器会发送当前缓存状态作为初始快照。

### 7.3 客户端协议

客户端发送 JSON 消息来订阅/取消订阅频道：

```json
// 订阅
{"action": "subscribe", "channel": "ticker:BTCUSDT"}

// 取消订阅
{"action": "unsubscribe", "channel": "orderbook:ETHUSDT"}
```

**频道验证:** 仅接受以下格式：
- 策略频道：`strategy/positions`、`strategy/trades`、`strategy/account`、`strategy/orders`、`strategy/funding`（连接时自动订阅）
- 市场频道：`ticker:{SYMBOL}`、`orderbook:{SYMBOL}`、`kline:{SYMBOL}`（需显式订阅；交易对必须匹配 `[A-Z0-9]{2,20}`）

无效频道会收到错误响应：`{"error": "Invalid channel: ..."}`。

所有服务器推送的消息均包含 `"channel"` 字段，客户端可据此进行路由。所有 `strategy/*` 频道的负载还包含 `"strategyId"` 字段（UUID 字符串），用于标识产生该事件的策略。

### 7.4 频道 (事件)

#### 7.4.1 `strategy/positions`
持仓变更更新（新增、更新、平仓）。连接时自动订阅。

*   **方向:** 服务器 -> 客户端
*   **快照（连接时）:** 通过 gRPC `GetPositions` 获取所有运行中策略的持仓。
*   **响应负载:**
    ```json
    {
      "channel": "strategy/positions",
      "strategyId": "a1b2c3d4-...",
      "type": "update",
      "data": [
        {
          "symbol": "BTCUSDT",
          "side": "Long",
          "leverage": 20,
          "size": 0.6,
          "entryPrice": 97500.0,
          "markPrice": 98200.0,
          "unrealizedPnl": 420.0,
          "openTime": 1707667200000
        }
      ]
    }
    ```
    `type` 在初始连接时为 `"snapshot"`，增量变更时为 `"update"`。

#### 7.4.2 `strategy/trades`
新成交执行时立即推送。连接时自动订阅。

*   **方向:** 服务器 -> 客户端
*   **响应负载:**
    ```json
    {
      "channel": "strategy/trades",
      "strategyId": "a1b2c3d4-...",
      "tradeId": "100002",
      "time": 1707667205000,
      "symbol": "BTCUSDT",
      "action": "Open Long",
      "price": 98100.0,
      "quantity": 0.1,
      "realizedPnl": 0.0       // 来自 ME 的逐笔盈亏（开仓交易为 0）
    }
    ```

> **新增字段 (D-01)：** `realizedPnl` 现已包含在 WebSocket 成交推送负载中。

#### 7.4.3 `strategy/account`
账户权益和余额更新。连接时自动订阅。

*   **方向:** 服务器 -> 客户端
*   **快照来源（连接时）:** 后端优先使用策略 `engine_account_id` 调用 MatchX `GetAccount` 获取快照；若不可用，则回退到 DB `strategy.total_equity`，余额相关字段可为空。
*   **响应负载:**
    ```json
    {
      "channel": "strategy/account",
      "strategyId": "a1b2c3d4-...",
      "totalEquity": 10350.50,
      "availableBalance": 5000.00,
      "unrealizedPnl": 350.50,
      "walletBalance": 10000.00,
      "totalInitialMargin": 1500.00
    }
    ```

#### 7.4.4 `strategy/orders`
订单生命周期更新（来自账户事件流 `order_update`）。连接时自动订阅。

*   **方向:** 服务器 -> 客户端
*   **响应负载（示例）:**
    ```json
    {
      "channel": "strategy/orders",
      "strategyId": "a1b2c3d4-...",
      "type": "update",
      "data": [
        {
          "orderId": "12345",
          "symbol": "BTCUSDT",
          "orderType": "LIMIT",
          "side": "BUY",
          "positionSide": "Long",
          "status": "NEW",
          "quantity": 0.1,
          "filledQty": 0.0
        }
      ]
    }
    ```

#### 7.4.5 `strategy/funding`
资金费更新（来自账户事件流 `funding_update`）。连接时自动订阅。

*   **方向:** 服务器 -> 客户端
*   **响应负载（示例）:**
    ```json
    {
      "channel": "strategy/funding",
      "strategyId": "a1b2c3d4-...",
      "type": "update",
      "data": [
        {
          "fundingTime": 1707667200000,
          "symbol": "BTCUSDT",
          "positionSide": "Long",
          "fundingRate": 0.0001,
          "fundingFee": -1.25
        }
      ]
    }
    ```

#### 7.4.6 `ticker:{symbol}`
指定交易对的实时价格更新。

*   **订阅:** 客户端需发送 `{"action": "subscribe", "channel": "ticker:BTCUSDT"}`。订阅后服务器会发送当前缓存的 ticker 作为初始快照。
*   **响应负载:**
    ```json
    {
      "channel": "ticker:BTCUSDT",
      "symbol": "BTCUSDT",
      "price": 98205.0,
      "timestamp": 1707667206000
    }
    ```
    > 说明：当前 `SubscribeTicker` 流仅包含 `symbol`、`price` 和 `timestamp`。

#### 7.4.7 `orderbook:{symbol}`
指定交易对的盘口数据更新。

*   **订阅:** 客户端需发送 `{"action": "subscribe", "channel": "orderbook:BTCUSDT"}`。订阅后服务器会发送当前缓存的盘口作为初始快照。
*   **响应负载:**
    ```json
    {
      "channel": "orderbook:BTCUSDT",
      "symbol": "BTCUSDT",
      "bids": [["98200.0", "0.5"], ["98199.5", "1.2"]],
      "asks": [["98201.0", "0.3"], ["98202.0", "0.8"]],
      "timestamp": 1707667206000
    }
    ```

#### 7.4.8 `kline:{symbol}`
指定交易对的实时 K 线更新。

*   **订阅:** 客户端需发送 `{"action": "subscribe", "channel": "kline:BTCUSDT"}`。订阅后服务器会发送当前缓存中的最新 K 线作为初始快照。
*   **响应负载（示例）:**
    ```json
    {
      "channel": "kline:BTCUSDT",
      "type": "snapshot",
      "data": {
        "symbol": "BTCUSDT",
        "interval": "1m",
        "openTime": 1707667200000,
        "open": 98000.0,
        "high": 98500.0,
        "low": 97900.0,
        "close": 98200.0,
        "volume": 150.5,
        "closeTime": 1707667259999,
        "isFinal": true
      }
    }
    ```

---

## 8. 系统架构与协议

后端与匹配引擎 (MatchX) 完全通过 **gRPC** 通信。后端作为 **gRPC 客户端**，既发起 Unary RPC 调用，也订阅服务端流式 RPC。数据从 ME 流经内部 Redis pub/sub 层传输到 WebSocket 客户端。

### 8.1 后端 <-> 匹配引擎 矩阵

| 数据流 | 方向 | 协议 | 实施策略 |
| :--- | :--- | :--- | :--- |
| **账户管理** | BE → ME | **gRPC (Unary)** | `CreateAccount`、`GetAccount`、`GetPositions` 等按需查询。 |
| **订单管理** | BE → ME | **gRPC (Unary)** | `PlaceOrder`、`CancelOrder`、`AdjustLeverage`。同步确认。 |
| **策略生命周期** | BE → ME | **gRPC (Unary)** | **ME 尚未实现。** 启动/停止当前仅为 DB 状态转换。 |
| **市场数据** | ME → BE | **gRPC (Streaming)** | `SubscribeTicker`、`SubscribeOrderBook`、`SubscribeKline`。流消费者桥接到内存缓存 + Redis pub/sub。 |
| **账户事件** | ME → BE | **gRPC (Streaming)** | `SubscribeAccountEvents`。传递订单、交易、持仓、账户与资金费更新。通过后台工作进程与 WS 桥接进行持久化/转发。 |

### 8.2 gRPC 服务定义 (内部)

> **Proto 源文件:** `protos/matchx/`（8 个 proto 文件，package `matchx`）
>
> **端口配置:**
> | 服务 | 默认端口 | 环境变量 |
> | :--- | :--- | :--- |
> | ME / MatchX 引擎 | `50051` (本地) / `6012` (staging) | `ME_GRPC_HOST` + `ME_GRPC_PORT` |

#### 8.2.1 `MatchXService`（22 个 Unary RPC — BE → ME）

后端使用的关键 RPC：

| RPC | 用途 |
| :--- | :--- |
| `CreateAccount` | 注册用户账户并设定初始资金 |
| `GetAccount` | 查询账户状态（权益、余额） |
| `GetPositions` | 查询持仓及实时 PnL |
| `PlaceOrder` / `CancelOrder` | 订单管理 |
| `GetPerformanceSummary` | 策略 KPI |
| `GetDailyReturns` / `GetAssetCurve` | 分析数据 |
| `GetSymbols` / `GetOrderBook` / `GetKlines` | 市场数据查询 |

#### 8.2.2 `MatchXStreamService`（4 个 Streaming RPC — ME → BE）

| RPC | 传递事件 | 后端处理 |
| :--- | :--- | :--- |
| `SubscribeTicker(symbol)` | 每个交易对的价格更新 | 更新内存缓存 + 发布到 Redis `market:ticker:{symbol}` |
| `SubscribeOrderBook(symbol)` | 盘口快照 | 更新内存缓存 + 发布到 Redis `market:orderbook:{symbol}` |
| `SubscribeKline(symbol)` | K 线更新 | 更新内存缓存 + 发布到 Redis `market:kline:{symbol}` |
| `SubscribeAccountEvents(user_id)` | 交易、持仓、账户更新 | 交易和权益 → DB 队列；持仓 → 仅 Redis（不持久化到数据库） |

**账户事件类型**（通过 `SubscribeAccountEvents` 传递）：

- **`order_update`** — 订单生命周期更新 → 发布到 `ws:strategy/orders`（Redis/WS）。
- **`trade_update`** — 新的成交执行 → 持久化到 `trades` 表（含 `realized_pnl`），发布到 `ws:strategy/trades`。注意：REST `GET /trades` 现在从 gRPC `GetTradeHistory` Unary RPC 读取，不再从数据库读取。
- **`position_update`** — 仓位开仓/变更 → 发布到 `ws:strategy/positions`（仅 Redis，**不再**持久化到数据库）。REST 端点通过 gRPC `GetPositions` / `GetPositionHistory` Unary RPC 按需获取持仓数据。
- **`account_update`** — 权益快照 → 持久化到 `equity_snapshots` 表（用于分析计算：每日收益、资产曲线、夏普比率），发布到 `ws:strategy/account`。
- **`funding_update`** — 资金费更新 → 发布到 `ws:strategy/funding`（Redis/WS）。

### 8.3 Redis 消息格式 (内部: 流消费者 → WebSocket)

流消费者发布到 Redis pub/sub 频道。WebSocket 处理器订阅并转发给已连接的客户端。

> **注意:** 盘口价格/数量值使用**字符串**以保持小数精度。

#### 8.3.1 频道: `market:ticker:{symbol}`
**频率:** 每次价格变动时。
```json
{
  "symbol": "BTCUSDT",
  "price": 98205.5,
  "timestamp": 1707667206000
}
```

#### 8.3.2 频道: `market:orderbook:{symbol}`
**频率:** 每次 ME 流更新盘口时。
```json
{
  "symbol": "BTCUSDT",
  "bids": [["98200.0", "0.5"], ["98199.5", "1.2"]],
  "asks": [["98201.0", "0.3"], ["98202.0", "0.8"]],
  "timestamp": 1707667206100
}
```
