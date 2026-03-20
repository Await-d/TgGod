# Agent 03: MessageList 组件

## 任务目标
创建消息列表组件，支持虚拟滚动和高性能渲染。

## 输出文件
- `frontend/src/components/Chat/MessageList/MessageList.tsx`
- `frontend/src/components/Chat/MessageList/MessageList.module.css`
- `frontend/src/components/Chat/MessageList/MessageItem.tsx`
- `frontend/src/components/Chat/MessageList/MessageItem.module.css`

## 功能需求

### 核心功能
1. **消息渲染**
   - 文本消息
   - 图片消息（缩略图+预览）
   - 视频消息（封面+播放）
   - 文件消息（图标+下载）
   - 时间戳显示

2. **虚拟滚动**
   - 使用react-window或react-virtualized
   - 支持大量消息（1000+）
   - 平滑滚动体验

3. **加载更多**
   - 滚动到顶部加载历史消息
   - 加载指示器
   - 自动定位到新消息

4. **交互功能**
   - 消息选择
   - 右键菜单
   - 图片/视频预览
   - 文件下载

## 技术要求

### 组件接口
```typescript
interface MessageListProps {
  messages: Message[];
  loading?: boolean;
  hasMore?: boolean;
  onLoadMore?: () => void;
  onMessageClick?: (message: Message) => void;
  onDownload?: (message: Message) => void;
  className?: string;
}

interface Message {
  id: string;
  type: 'text' | 'image' | 'video' | 'file';
  content: string;
  sender: string;
  timestamp: Date;
  mediaUrl?: string;
  thumbnailUrl?: string;
  fileSize?: number;
  fileName?: string;
}
```

### 设计规范
- 背景：`#f8f9fa`
- 消息气泡：白色 `#ffffff`
- 阴影：`0 1px 2px rgba(0, 0, 0, 0.05)`
- 间距：消息间12px
- 内边距：16px
- 圆角：12px
- 最大宽度：70%（桌面）/ 85%（移动）

### 消息类型样式
- **文本**：普通气泡
- **图片**：圆角图片+点击放大
- **视频**：封面+播放按钮
- **文件**：图标+文件名+大小

## 实现要点

1. **虚拟滚动实现**
   ```typescript
   import { FixedSizeList } from 'react-window';

   <FixedSizeList
     height={containerHeight}
     itemCount={messages.length}
     itemSize={80}
     width="100%"
   >
     {({ index, style }) => (
       <div style={style}>
         <MessageItem message={messages[index]} />
       </div>
     )}
   </FixedSizeList>
   ```

2. **加载更多检测**
   - 使用IntersectionObserver
   - 或监听滚动事件

3. **性能优化**
   - MessageItem使用React.memo
   - 图片懒加载
   - 使用useCallback包装回调

4. **媒体预览**
   - 图片：使用Ant Design Image组件
   - 视频：使用HTML5 video标签
   - 文件：提供下载链接

## 代码限制
- MessageList.tsx不超过200行
- MessageItem.tsx不超过150行
- 每个CSS文件不超过200行

## 测试要点
- 大量消息渲染性能
- 虚拟滚动流畅度
- 加载更多功能
- 不同消息类型显示
- 图片/视频预览
- 响应式布局

## 参考资源
- 现有实现：`frontend/src/pages/ChatInterface.tsx`（查看现有消息渲染逻辑）
- react-window文档：https://react-window.vercel.app/

## 完成标准
- ✅ 组件创建完成
- ✅ 虚拟滚动实现
- ✅ 所有消息类型支持
- ✅ 性能优化到位
- ✅ 响应式适配良好
- ✅ 无TypeScript错误
