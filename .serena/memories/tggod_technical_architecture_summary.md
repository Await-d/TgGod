# TgGod 项目技术架构总结

## 前端技术栈
- **框架**: React 18 + TypeScript
- **UI 库**: Ant Design 5.x
- **状态管理**: React Hooks + Context API
- **样式管理**: CSS Modules + 传统 CSS
- **构建工具**: Create React App + Webpack
- **网络请求**: Axios
- **实时通信**: WebSocket

## 后端技术栈
- **框架**: FastAPI + Python 3.11
- **数据库**: SQLite (支持 PostgreSQL)
- **ORM**: SQLAlchemy 2.x
- **数据库迁移**: Alembic
- **认证**: JWT + OAuth2
- **异步处理**: AsyncIO
- **实时通信**: WebSocket
- **Telegram API**: Telethon

## 核心功能模块

### 1. 用户认证和管理
- JWT 令牌认证
- 用户角色管理
- Telegram 账户绑定

### 2. 群组管理
- 群组同步和监控
- 群组信息统计
- 群组活跃状态管理

### 3. 消息处理
- 实时消息同步
- 消息过滤和规则
- 媒体文件处理
- 转发消息预览
- 消息搜索和分页

### 4. 数据库架构
- 用户表 (users)
- 群组表 (telegram_groups)
- 消息表 (telegram_messages)
- 过滤规则表 (filter_rules)
- 系统日志表 (system_logs)

## 项目结构

```
TgGod/
├── frontend/                 # React 前端
│   ├── src/
│   │   ├── components/      # 组件
│   │   │   ├── Chat/       # 聊天相关组件
│   │   │   └── Common/     # 通用组件
│   │   ├── pages/          # 页面组件
│   │   ├── services/       # API 服务
│   │   ├── types/          # TypeScript 类型定义
│   │   └── utils/          # 工具函数
│   └── public/             # 静态资源
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务逻辑
│   │   ├── utils/          # 工具函数
│   │   └── websocket/      # WebSocket 管理
│   ├── alembic/            # 数据库迁移
│   └── data/               # 数据存储
└── docs/                   # 文档
```

## 关键特性

### 1. 实时数据同步
- WebSocket 连接管理
- 消息实时推送
- 群组状态同步

### 2. 消息过滤系统
- 自定义过滤规则
- 关键词过滤
- 媒体类型过滤
- 用户过滤

### 3. 媒体文件管理
- 图片、视频、音频预览
- 文件下载和存储
- 媒体文件压缩

### 4. 用户界面
- 响应式设计
- 移动端适配
- 暗色主题支持
- 可自定义界面

## 数据库管理

### 自动化工具
- `check_database.py` - 数据库检查和修复
- `start_app.py` - 集成检查的启动器
- `migrate.py` - 手动迁移工具

### 迁移管理
- Alembic 版本控制
- 自动迁移检测
- 数据库结构同步

## 部署和运维

### 开发环境
```bash
# 前端开发
npm start

# 后端开发
python start_app.py
```

### 生产环境
- Docker 容器化部署
- Nginx 反向代理
- SSL 证书配置
- 日志管理

## 性能优化

### 前端优化
- 代码分割和懒加载
- 组件缓存
- 图片懒加载
- 虚拟滚动

### 后端优化
- 数据库连接池
- 异步处理
- 缓存机制
- API 限流

## 安全特性

### 认证安全
- JWT 令牌管理
- 密码加密存储
- 会话管理

### 数据安全
- SQL 注入防护
- XSS 攻击防护
- CSRF 保护
- 数据加密传输

## 监控和日志

### 系统监控
- 应用性能监控
- 数据库性能监控
- 错误追踪

### 日志管理
- 结构化日志
- 日志分级
- 日志轮转

## 测试策略

### 前端测试
- Jest 单元测试
- React Testing Library
- 端到端测试

### 后端测试
- pytest 单元测试
- API 集成测试
- 数据库测试

## 文档和维护

### 技术文档
- API 文档 (OpenAPI/Swagger)
- 数据库文档
- 部署文档

### 代码质量
- TypeScript 类型检查
- ESLint 代码检查
- Prettier 代码格式化
- 代码审查流程