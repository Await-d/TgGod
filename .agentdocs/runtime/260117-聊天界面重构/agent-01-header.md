# Agent 01: ChatHeader 组件

## 任务目标
创建聊天界面头部组件，支持多设备响应式布局。

## 输出文件
- `frontend/src/components/Chat/Header/ChatHeader.tsx`
- `frontend/src/components/Chat/Header/ChatHeader.module.css`

## 功能需求

### 核心功能
1. **群组信息显示**
   - 群组头像
   - 群组名称
   - 在线人数/成员数

2. **操作按钮**
   - 侧边栏切换按钮（移动端）
   - 搜索按钮
   - 更多操作菜单

3. **响应式适配**
   - 移动端：紧凑布局，显示汉堡菜单
   - 平板：中等布局
   - 桌面：完整布局

## 技术要求

### 组件接口
```typescript
interface ChatHeaderProps {
  groupName: string;
  groupAvatar?: string;
  memberCount?: number;
  onlineCount?: number;
  onToggleSidebar?: () => void;
  onSearch?: () => void;
  showSidebarToggle?: boolean;
  className?: string;
}
```

### 设计规范
- 高度：64px（桌面）/ 56px（移动）
- 背景：渐变白色 `linear-gradient(180deg, #ffffff 0%, #fafbfc 100%)`
- 边框：底部 1px `rgba(0, 0, 0, 0.06)`
- 阴影：`0 1px 3px rgba(0, 0, 0, 0.02)`
- 字体：SF Pro Display / Segoe UI
- 图标：使用 Ant Design Icons

### 响应式断点
- 移动端：≤768px
- 平板：769-1024px
- 桌面：≥1025px

## 实现要点

1. **使用 useResponsiveLayout Hook**
   ```typescript
   import { useResponsiveLayout } from '../../../hooks/useResponsiveLayout';
   const { isMobile, isTablet, isDesktop } = useResponsiveLayout();
   ```

2. **CSS Modules**
   - 使用 `.module.css` 文件
   - 类名遵循 BEM 命名规范
   - 支持暗色模式

3. **性能优化**
   - 使用 React.memo
   - 回调函数使用 useCallback

4. **无障碍支持**
   - 添加 aria-label
   - 键盘导航支持

## 代码限制
- 组件文件不超过150行
- CSS文件不超过200行
- 避免过度抽象

## 测试要点
- 不同设备尺寸下的显示
- 按钮点击响应
- 暗色模式切换
- 长文本处理

## 参考资源
- 布局常量：`frontend/src/constants/chatLayout.ts`
- 响应式Hook：`frontend/src/hooks/useResponsiveLayout.ts`
- 现有ChatInterface：`frontend/src/pages/ChatInterface.tsx`（参考现有实现）

## 完成标准
- ✅ 组件创建完成
- ✅ 响应式适配正常
- ✅ 样式符合设计规范
- ✅ 代码质量良好
- ✅ 无TypeScript错误
