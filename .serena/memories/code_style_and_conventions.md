# TgGod 代码风格和约定

## 后端代码风格 (Python)

### 基本约定
- **Python版本**: 3.8+
- **编码风格**: 遵循PEP 8标准
- **文档字符串**: 使用中文详细描述，包含参数、返回值和示例
- **类型提示**: 使用Python类型注解
- **异步编程**: 广泛使用async/await模式

### 文件和目录结构
```
backend/app/
├── main.py           # FastAPI应用入口
├── config.py         # 配置管理
├── database.py       # 数据库配置
├── api/             # API路由按域组织
├── models/          # SQLAlchemy数据模型
├── services/        # 业务逻辑服务
├── websocket/       # WebSocket处理
├── utils/           # 工具函数
└── core/            # 核心功能模块
```

### 命名约定
- **文件名**: 小写字母+下划线 (`telegram_service.py`)
- **类名**: 大驼峰命名 (`FilterRule`, `DownloadTask`)
- **函数名**: 小写字母+下划线 (`get_message_history`)
- **常量**: 全大写+下划线 (`DATABASE_URL`, `MAX_FILE_SIZE`)
- **变量**: 小写字母+下划线 (`message_count`, `api_client`)

### 数据库模型约定
```python
class FilterRule(Base):
    """详细的中文文档字符串
    
    描述模型的用途、字段含义和关系
    包含使用示例和注意事项
    """
    __tablename__ = "filter_rules"
    
    # 主键
    id = Column(Integer, primary_key=True, index=True)
    
    # 字符串字段指定长度
    name = Column(String(255), nullable=False)
    
    # JSON字段用于复杂数据
    keywords = Column(JSON, nullable=True)
    
    # 时间字段使用timezone=True
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系定义
    task_associations = relationship("TaskRuleAssociation", back_populates="rule")
```

### 服务类约定
```python
class TelegramService:
    """服务类使用单例模式或依赖注入"""
    
    def __init__(self):
        self.client = None
        self.is_connected = False
    
    async def async_method(self, param: str) -> dict:
        """异步方法统一使用async/await
        
        Args:
            param: 参数描述
            
        Returns:
            dict: 返回值描述
            
        Raises:
            Exception: 异常情况描述
        """
        pass
```

### API路由约定
```python
@router.get("/groups", response_model=List[TelegramGroupResponse])
async def get_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """API端点使用依赖注入模式
    
    统一的错误处理和响应格式
    """
    pass
```

## 前端代码风格 (React + TypeScript)

### 基本约定
- **TypeScript**: 严格类型检查
- **组件化**: 功能拆分为可复用组件
- **Hooks**: 优先使用函数组件和React Hooks
- **状态管理**: Zustand用于全局状态
- **UI组件**: Ant Design设计语言

### 文件和目录结构
```
frontend/src/
├── components/      # 可复用组件
├── pages/          # 页面组件
├── services/       # API服务层
├── store/          # Zustand状态管理
├── types/          # TypeScript类型定义
├── hooks/          # 自定义Hooks
├── utils/          # 工具函数
└── styles/         # 样式文件
```

### 命名约定
- **组件名**: 大驼峰命名 (`MainLayout.tsx`, `UserSettings.tsx`)
- **文件名**: 大驼峰命名 (组件) 或小驼峰 (工具)
- **变量/函数**: 小驼峰命名 (`messageCount`, `handleSubmit`)
- **接口/类型**: 大驼峰命名 (`User`, `ApiResponse`)
- **常量**: 全大写+下划线 (`API_BASE_URL`)

### 组件定义约定
```typescript
interface Props {
  title: string;
  onSubmit: (data: FormData) => void;
  loading?: boolean;
}

const MyComponent: React.FC<Props> = ({ title, onSubmit, loading = false }) => {
  // 状态定义
  const [data, setData] = useState<string>('');
  
  // 副作用
  useEffect(() => {
    // 初始化逻辑
  }, []);
  
  // 事件处理
  const handleClick = useCallback(() => {
    // 处理逻辑
  }, []);
  
  return (
    <div>
      {/* JSX内容 */}
    </div>
  );
};

export default MyComponent;
```

### 状态管理约定 (Zustand)
```typescript
interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: false,
  
  login: async (credentials) => {
    // 登录逻辑
    set({ user: result.user, isAuthenticated: true });
  },
  
  logout: () => {
    set({ user: null, isAuthenticated: false });
  },
}));
```

## 通用约定

### 注释和文档
- **中文注释**: 代码注释使用中文
- **详细文档**: 复杂功能提供详细说明
- **API文档**: FastAPI自动生成OpenAPI文档
- **README**: 中英文对照的使用说明

### 错误处理
```python
# 后端错误处理
try:
    result = await some_operation()
    return {"success": True, "data": result}
except SpecificException as e:
    logger.error(f"具体错误描述: {e}")
    raise HTTPException(status_code=400, detail="用户友好的错误信息")
```

```typescript
// 前端错误处理
try {
  const result = await apiCall();
  return result;
} catch (error) {
  console.error('操作失败:', error);
  message.error('操作失败，请重试');
  throw error;
}
```

### 日志约定
- **结构化日志**: 使用统一的日志格式
- **日志级别**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **中文描述**: 日志信息使用中文描述
- **关键信息**: 记录操作用户、时间、结果

### 配置管理
- **环境变量**: 敏感信息通过环境变量配置
- **默认值**: 提供合理的默认配置
- **验证**: 启动时验证必要配置项
- **文档**: 配置项要有详细说明

### 测试约定
- **单元测试**: 核心业务逻辑需要单元测试
- **集成测试**: API端点需要集成测试
- **测试数据**: 使用模拟数据，不依赖真实环境
- **覆盖率**: 保持合理的测试覆盖率

### Git提交约定
```
feat: 添加新功能
fix: 修复bug
docs: 更新文档
style: 代码格式调整
refactor: 重构代码
test: 添加测试
chore: 构建工具或辅助工具的变动
```