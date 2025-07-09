# Backend Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI应用入口
│   ├── config.py         # 配置管理
│   ├── database.py       # 数据库连接
│   ├── models/           # 数据模型
│   │   ├── __init__.py
│   │   ├── telegram.py   # Telegram相关模型
│   │   ├── rule.py       # 规则模型
│   │   └── log.py        # 日志模型
│   ├── api/              # API路由
│   │   ├── __init__.py
│   │   ├── telegram.py   # Telegram API
│   │   ├── rule.py       # 规则管理API
│   │   └── log.py        # 日志API
│   ├── services/         # 业务逻辑
│   │   ├── __init__.py
│   │   ├── telegram_service.py
│   │   ├── rule_service.py
│   │   └── notification_service.py
│   ├── utils/            # 工具函数
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   └── helpers.py
│   └── websocket/        # WebSocket处理
│       ├── __init__.py
│       └── manager.py
├── requirements.txt      # Python依赖
├── Dockerfile           # Docker配置
└── .env.example         # 环境变量示例
```