# Agent 02: ChatSidebar 组件

## 任务目标
创建聊天侧边栏组件，展示群组列表，支持搜索和过滤。

## 输出文件
- `frontend/src/components/Chat/Sidebar/ChatSidebar.tsx`
- `frontend/src/components/Chat/Sidebar/ChatSidebar.module.css`
- `frontend/src/components/Chat/Sidebar/GroupListItem.tsx`
- `frontend/src/components/Chat/Sidebar/GroupListItem.module.css`

## 功能需求

### 核心功能
1. **群组列表**
   - 显示所有群组
   - 群组头像、名称
   - 最后消息预览
   - 未读消息数量徽章

2. **搜索功能**
   - 实时搜索过滤
   - 高亮匹配文本

3. **选中状态**
   - 当前选中群组高亮
   - 点击切换群组

4. **响应式适配**
   - 移动端：抽屉模式（85%宽度）
   - 平板：固定侧边栏（280px）
   - 桌面：可调整大小（260-420px）

## 技术要求

### 组件接口
```typescript
interface ChatSidebarProps {
  groups: GroupInfo[];
  selectedGroupId?: string;
  onSelectGroup: (groupId: string) => void;
  onSearch?: (keyword: string) => void;
  className?: string;
}

interface GroupInfo {
  id: string;
  name: string;
  avatar?: string;
  lastMessage?: string;
  lastMessageTime?: Date;
  unreadCount?: number;
}
```

### 设计规范
- 宽度：移动85% / 平板280px / 桌面320px
- 背景：白色 `#ffffff`
- 边框：右侧 1px `rgba(0, 0, 0, 0.06)`
- 阴影：`2px 0 12px rgba(0, 0, 0, 0.03)`
- 列表项高度：72px
- 选中项背景：`#f0f5ff`
- 悬停背景：`#fafafa`

### 子组件：GroupListItem
- 独立的列表项组件
- 支持头像、标题、副标题、徽章
- 点击和悬停效果

## 实现要点

1. **虚拟滚动（可选）**
   - 如果群组数量>100，考虑使用react-window
   - 否则使用普通列表

2. **搜索优化**
   - 使用debounce防抖
   - 本地过滤，避免频繁请求

3. **性能优化**
   - GroupListItem使用React.memo
   - 使用useCallback包装回调

4. **无障碍支持**
   - 列表使用role="list"
   - 项目使用role="listitem"
   - 键盘导航（上下箭头）

## 代码限制
- ChatSidebar.tsx不超过150行
- GroupListItem.tsx不超过100行
- 每个CSS文件不超过150行

## 测试要点
- 群组列表渲染
- 搜索过滤功能
- 选中状态切换
- 响应式布局
- 长文本截断

## 参考资源
- 布局常量：`frontend/src/constants/chatLayout.ts`
- 现有实现：`frontend/src/pages/ChatInterface.tsx`（查看现有群组列表逻辑）

## 完成标准
- ✅ 组件创建完成
- ✅ 搜索功能正常
- ✅ 选中状态管理正确
- ✅ 响应式适配良好
- ✅ 无TypeScript错误
