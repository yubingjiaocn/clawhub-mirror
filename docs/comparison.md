# ClawHub vs clawhub-mirror 功能对比

## 定位

| | ClawHub (官方) | clawhub-mirror |
|---|---|---|
| **定位** | 公共 skill registry（类似 npmjs.com） | 企业私有 registry + 外部 skill 准入代理 |
| **部署** | SaaS only (clawhub.ai) | Self-hosted（Docker / 裸机） |
| **目标用户** | 开源社区、个人开发者 | 企业内部、有安全合规需求的团队 |

## 核心 API 兼容性

| API Endpoint | ClawHub | clawhub-mirror | 备注 |
|---|---|---|---|
| `/.well-known/clawhub.json` | ✅ | ✅ | Discovery 协议，CLI 自动识别 |
| `GET /api/v1/resolve` | ✅ | ✅ | 版本解析（slug + hash） |
| `GET /api/v1/download` | ✅ | ✅ | 下载 skill zip |
| `GET /api/v1/search` | ✅ | ✅ | ClawHub 用 OpenAI embedding 向量搜索；mirror 用 SQLite FTS5 |
| `GET /api/v1/skills` | ✅ | ✅ | 分页列表 |
| `GET /api/v1/skills/:slug` | ✅ | ✅ | 详情 + latest version |
| `GET /api/v1/skills/:slug/versions` | ✅ | ✅ | 版本列表 |
| `POST /api/v1/skills` | ✅ | ✅ | 发布（multipart upload） |
| `DELETE /api/v1/skills/:slug` | ✅ | ✅ | 软删除 |
| `GET /api/v1/whoami` | ✅ | ✅ | 当前用户信息 |
| `POST /api/v1/skills/:slug/undelete` | ✅ | ❌ | 恢复已删除 skill |
| `POST /api/v1/stars/:slug` | ✅ | ❌ | 收藏 |
| `POST /api/v1/skills/:slug/rename` | ✅ | ❌ | 重命名（保留旧 slug 重定向） |
| `POST /api/v1/skills/:slug/merge` | ✅ | ❌ | 合并重复 skill |
| `POST /api/v1/transfers` | ✅ | ❌ | 所有权转移 |
| `/api/v1/packages` | ✅ | ❌ | OpenClaw 代码插件目录 |
| `/api/v1/plugins` | ✅ | ❌ | 插件列表 |
| `/api/v1/souls` | ✅ | ❌ | SOUL.md registry (onlycrabs.ai) |
| `GET /healthz` | ❌ | ✅ | 健康检查 |

## 企业特有功能（clawhub-mirror 独有）

| 功能 | ClawHub | clawhub-mirror |
|---|---|---|
| **Mirror/Proxy 模式** | ❌ | ✅ 内部 skill 直接返回，外部走代理+缓存 |
| **准入白名单** | ❌ | ✅ 按 slug + 可选版本锁定 |
| **审批工作流** | ❌ | ✅ pending request → admin approve/deny |
| **版本锁定（pin）** | ❌ | ✅ 白名单可限制特定版本 |
| **RBAC（角色控制）** | 有（admin/moderator/user） | ✅ admin/publisher/reader |
| **API Token 认证** | ✅ GitHub OAuth + API token | ✅ Bearer token（bcrypt） |
| **用户管理 API** | 通过 GitHub 身份 | ✅ REST API 创建/停用用户 |
| **准入策略 CRUD** | ❌ | ✅ `/api/v1/admin/policies` |
| **Pending 审批队列** | ❌ | ✅ `/api/v1/admin/policies/pending` |
| **本地 zip 缓存** | N/A | ✅ 代理过的外部 skill 缓存到 S3/本地 |

## 安全

| | ClawHub | clawhub-mirror |
|---|---|---|
| **VirusTotal 扫描** | ✅ 所有提交自动扫描 | ❌（可自行集成） |
| **LLM 安全分析** | ✅ AI 检测 prompt injection | ❌（可对接 skill-guard） |
| **Moderation 状态** | ✅ clean/suspicious/malicious | ❌ |
| **恶意 skill 拦截** | ✅ isMalwareBlocked 阻止下载 | 通过白名单间接实现 |
| **供应链隔离** | ❌ 所有人可发布 | ✅ 只有 admin 审批的才能进入内部 |

## 搜索

| | ClawHub | clawhub-mirror |
|---|---|---|
| **搜索引擎** | OpenAI text-embedding-3-small 向量搜索 | SQLite FTS5 全文搜索 |
| **Typo tolerance** | ✅ 向量搜索天然支持 | ❌ 精确匹配 + 前缀 |
| **语义搜索** | ✅ | ❌ |
| **搜索范围** | slug + displayName + summary | slug + displayName + summary |

## 存储 & 数据库

| | ClawHub | clawhub-mirror |
|---|---|---|
| **数据库** | Convex (serverless) | SQLite（默认）/ PostgreSQL（切换 URL 即可） |
| **文件存储** | Convex file storage | S3 兼容（MinIO/AWS S3）或本地文件系统 |
| **版本管理** | Convex 内置 | SQLAlchemy + 数据库记录 |

## 部署

| | ClawHub | clawhub-mirror |
|---|---|---|
| **部署方式** | SaaS | Docker Compose / 单进程 |
| **依赖** | Convex Cloud + OpenAI API | Python 3.12 + SQLite（零外部依赖） |
| **最小部署** | N/A | 单个 Python 进程 + SQLite 文件 |
| **生产部署** | N/A | Docker Compose（app + Postgres + MinIO） |
| **水平扩展** | Convex 自动 | 切换 Postgres 后多实例 + 共享存储 |

## CLI 兼容性

| 操作 | ClawHub CLI | 对接 clawhub-mirror |
|---|---|---|
| `clawhub search` | ✅ | ✅ `CLAWHUB_URL=http://mirror:8080` |
| `clawhub install` | ✅ | ✅ |
| `clawhub publish` | ✅ | ✅ |
| `clawhub update` | ✅ | ✅（resolve + download） |
| `clawhub explore` | ✅ | ✅（list API） |
| `clawhub inspect` | ✅ | ✅（skill detail API） |
| `clawhub login` | ✅ GitHub OAuth | ⚠️ 需要用 API token（`CLAWHUB_TOKEN`） |
| `clawhub sync` | ✅ telemetry | ❌ telemetry endpoint 未实现 |

## 当前状态 & 待完善

### clawhub-mirror 原型已有
- ✅ 核心 ClawHub API 兼容（install 全链路可用）
- ✅ Mirror/proxy + 白名单准入
- ✅ 审批工作流（pending → approve/deny）
- ✅ RBAC + token 认证
- ✅ Docker 部署
- ✅ 18 个测试全通过

### 待做（生产化）
- 🔲 Web UI（管理面板：审批队列、skill 浏览、用户管理）
- 🔲 安全扫描集成（skill-guard / 自定义 webhook）
- 🔲 Webhook 自动导入（GitHub/GitLab push → 自动发布）
- 🔲 undelete / rename / merge API
- 🔲 下载统计和审计日志
- 🔲 LDAP/SSO 集成（企业认证）
- 🔲 telemetry sync endpoint
- 🔲 向量搜索（可选，pgvector）
- 🔲 速率限制
- 🔲 Helm chart / Terraform module
