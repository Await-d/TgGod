# Frontend Structure

```
frontend/
├── public/
│   ├── index.html
│   └── favicon.ico
├── src/
│   ├── components/       # 通用组件
│   │   ├── Layout/
│   │   ├── Loading/
│   │   └── Notification/
│   ├── pages/           # 页面组件
│   │   ├── Dashboard/   # 仪表板
│   │   ├── Groups/      # 群组管理
│   │   ├── Rules/       # 规则配置
│   │   ├── Downloads/   # 下载任务
│   │   └── Logs/        # 日志查看
│   ├── services/        # API服务
│   │   ├── api.ts
│   │   ├── telegram.ts
│   │   ├── rule.ts
│   │   └── websocket.ts
│   ├── store/           # 状态管理
│   │   ├── index.ts
│   │   ├── telegram.ts
│   │   └── rule.ts
│   ├── utils/           # 工具函数
│   │   ├── constants.ts
│   │   └── helpers.ts
│   ├── types/           # TypeScript类型
│   │   ├── telegram.ts
│   │   ├── rule.ts
│   │   └── api.ts
│   ├── App.tsx
│   └── index.tsx
├── package.json
├── tsconfig.json
└── tailwind.config.js
```