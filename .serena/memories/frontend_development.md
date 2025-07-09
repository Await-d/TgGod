# 前端开发配置

## 包管理器
- 使用 **pnpm** 进行开发和打包操作
- 更快的安装速度和更好的磁盘利用率

## 技术栈
- **React 18**: 现代化UI库
- **TypeScript**: 类型安全
- **Ant Design 5**: UI组件库
- **Zustand**: 轻量级状态管理
- **Socket.io**: WebSocket实时通信
- **Axios**: HTTP客户端
- **React Router**: 路由管理

## 开发命令
```bash
cd frontend
pnpm install        # 安装依赖
pnpm start         # 开发服务器
pnpm build         # 生产构建
pnpm test          # 运行测试
```

## 项目结构
```
frontend/src/
├── components/     # 通用组件
├── pages/         # 页面组件
├── services/      # API和WebSocket服务
├── store/         # Zustand状态管理
├── types/         # TypeScript类型定义
└── utils/         # 工具函数
```

## 已完成功能
- 完整的TypeScript类型系统
- WebSocket实时通信服务
- 状态管理架构
- 基础路由配置
- API服务封装