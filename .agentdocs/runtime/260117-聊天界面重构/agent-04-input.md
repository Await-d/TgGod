# Agent 04: ChatInput 组件

## 任务目标
创建聊天输入框组件，支持文本输入、文件上传和表情选择。

## 输出文件
- `frontend/src/components/Chat/Input/ChatInput.tsx`
- `frontend/src/components/Chat/Input/ChatInput.module.css`

## 功能需求

### 核心功能
1. **文本输入**
   - 多行文本框
   - 自动高度调整（最大5行）
   - Enter发送，Shift+Enter换行
   - 字符计数

2. **文件上传**
   - 图片上传（支持拖拽）
   - 视频上传
   - 文件上传
   - 上传进度显示
   - 文件预览

3. **表情选择**
   - 表情选择器
   - 常用表情快捷访问
   - 插入到光标位置

4. **快捷操作**
   - 发送按钮
   - 清空按钮
   - 附件按钮
   - 表情按钮

## 技术要求

### 组件接口
```typescript
interface ChatInputProps {
  onSend: (content: string, files?: File[]) => void;
  onUpload?: (files: File[]) => void;
  placeholder?: string;
  maxLength?: number;
  disabled?: boolean;
  loading?: boolean;
  className?: string;
}
```

### 设计规范
- 高度：80px（桌面）/ 72px（移动）
- 背景：白色 `#ffffff`
- 边框：顶部 1px `rgba(0, 0, 0, 0.06)`
- 阴影：`0 -1px 3px rgba(0, 0, 0, 0.02)`
- 输入框背景：`#f5f5f5`
- 输入框圆角：20px
- 按钮大小：36px
- 图标大小：20px

### 交互效果
- 输入框聚焦：边框高亮 `#1890ff`
- 按钮悬停：背景变深
- 发送按钮：主题色 `#1890ff`
- 禁用状态：灰色 `#d9d9d9`

## 实现要点

1. **自动高度调整**
   ```typescript
   const textareaRef = useRef<HTMLTextAreaElement>(null);

   const adjustHeight = () => {
     const textarea = textareaRef.current;
     if (textarea) {
       textarea.style.height = 'auto';
       textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
     }
   };
   ```

2. **文件上传**
   - 使用Ant Design Upload组件
   - 支持拖拽上传
   - 文件类型验证
   - 大小限制

3. **表情选择器**
   - 使用emoji-picker-react或自定义
   - 弹出层定位
   - 点击外部关闭

4. **键盘事件**
   ```typescript
   const handleKeyDown = (e: React.KeyboardEvent) => {
     if (e.key === 'Enter' && !e.shiftKey) {
       e.preventDefault();
       handleSend();
     }
   };
   ```

5. **性能优化**
   - 使用useCallback包装回调
   - 防抖处理输入事件
   - 文件上传使用Web Worker

## 代码限制
- ChatInput.tsx不超过200行
- CSS文件不超过150行

## 测试要点
- 文本输入和发送
- Enter/Shift+Enter行为
- 文件上传功能
- 表情选择和插入
- 自动高度调整
- 响应式布局
- 禁用状态

## 参考资源
- Ant Design Upload：https://ant.design/components/upload-cn/
- emoji-picker-react：https://www.npmjs.com/package/emoji-picker-react
- 现有实现：`frontend/src/pages/ChatInterface.tsx`

## 完成标准
- ✅ 组件创建完成
- ✅ 所有功能实现
- ✅ 文件上传正常
- ✅ 表情选择正常
- ✅ 键盘交互正确
- ✅ 响应式适配良好
- ✅ 无TypeScript错误
