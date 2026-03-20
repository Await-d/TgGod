# Agent 05: ChatContext 和集成

## 任务目标
创建ChatContext状态管理，集成所有组件到ChatInterface，完成重构。

## 输出文件
- `frontend/src/contexts/ChatContext.tsx`
- `frontend/src/pages/ChatInterface.refactored.tsx`（新版本）
- `frontend/src/pages/C - 群组列表
   - 当前选中群组
   - 群组切换

2. **消息状态**
   - 消息列表
   - 加载状态
   - 分页信息

3. **UI状态**
   - 侧边栏显示/隐藏
   - 搜索关键词
   - 加载指示器

4. **操作方法**
   - 加载群组
   - 加载消息
   - 发送消息
   - 切换群组

## 技术要求

### Context接口
```typescript
interface ChatContextValue {
  // 群组相关
  groups: GroupInfo[];
  selectedGroup: GroupInfo | null;
  selectGroup: (groupId: string) => von```

### 集成步骤
1. **创建ChatContext**
   - 使用useReducer或useState管理状态
   - 封装API调用逻辑
   - 提供Context Provider

2. **重构ChatInterface**
   - 使用ChatLayout组件
   - 组装Header、Sidebar、MessageList、Inponst ChatContext = createContext<ChatContextValue | null>(null);

   export const ChatProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
     // 状态管理
     const [groups, setGroups] = useState<GroupInfo[]>([]);
     const [messages, setMessages] = useState<Message[]>([]);
     // ... 其他状态

     // 方法实现
     const loadGroups = async () => { /* ... */ };
     const loadMessages = async (groupId: string) => { /* ... */ };
     // ... 其他方法

     return (
       <ChatContext.Provider value={{ /* ... */ }}>
         {children}
       </ChatContext.Provider>
     );
   };

   export const useChatContext = () => {
     const context = useContext(ChatContext);
     if (!context) throw new Error('useChatContext must be used within ChatProvider');
     return context;
   };
   ```

2. **ChatInterface重构**
   ```typescript
   export const ChatInterface: React.FC = () => {
     return (
       <ChatProvider>
         <ChatInterfaceContent />
       </ChatProvider>
     );
   };

   const ChatInterfaceContent: React.FC = () => {
     const chatContext = useChatContext();
     const { deviceType } = useResponsiveLayout();

     return (
       <ChatLayout
         sidebar={<ChatSidebar {...chatContext} />}
         header={<ChatHeader {...chatContext} />}
         main={<MessageList {...chatContext} />}
         footer={<ChatInput {...chatContext} />}
       />
     );
   };
   ```

3. **API集成**
   - 复用现有API调用
   - 保持与后端接口一致
   - 错误处理

4. **WebSocket集成**
   - 保留现有WebSocket连接
   - 实时消息更新
   - 状态同步

## 代码限制
- ChatContext.tsx不超过300行
- ChatInterface.refactored.tsx不超过150行

## 测试要点
- 所有功能正常工作
- 响应式布局正确
- 性能无明显下降
- 无TypeScript错误
- 无控制台警告

## 迁移策略
1. 创建新文件`ChatInterface.refactored.tsx`
2. 备份旧文件为`ChatInterface.tsx.backup`
3. 测试新版本
4. 确认无问题后替换旧文件

## 参考资源
- 现有实现：`frontend/src/pages/ChatInterface.tsx`
- API调用：查看现有API调用逻辑
- WebSocket：查看现有WebSocket连接

## 完成标准
- ✅ ChatContext创建完成
- ✅ 所有组件集成
- ✅ 功能完整迁移
- ✅ 测试通过
- ✅ 性能良好
- ✅ 无TypeScript错误

## 注意事项
⚠️ **此任务依赖Agent 01-04完成**
- 等待所有组件创建完成
- 确保组件接口一致
- 测试每个组件独立功能
