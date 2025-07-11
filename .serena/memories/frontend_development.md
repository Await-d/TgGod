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
│   └── Chat/      # 聊天界面组件
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

## 聊天界面功能
- **消息展示**: 完整的消息气泡界面
- **媒体支持**: 图片、视频、语音消息预览
- **Markdown支持**: 智能检测和渲染 (react-markdown + remark-gfm)
- **链接预览**: 自动识别和预览链接
- **布局优化**: 防止整体滚动条问题
- **移动端适配**: 完整的移动端手势和布局支持

## 打包信息
- **当前大小**: 551.29 kB (gzipped)
- **构建状态**: 成功，无编译错误
- **代码质量**: ESLint配置完整，只有警告无错误

## 依赖包
### Markdown相关
- react-markdown: Markdown渲染
- remark-gfm: GitHub Flavored Markdown支持
- rehype-highlight: 代码高亮
- highlight.js: 语法高亮库

### 布局相关
- 响应式设计完整
- 移动端手势支持
- 防滚动条优化