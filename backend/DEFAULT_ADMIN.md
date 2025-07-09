# 默认管理员账户使用说明

## 默认账户信息

系统会在首次启动时自动创建一个默认管理员账户：

- **用户名**: `admin`
- **密码**: `admin123`
- **邮箱**: `admin@tggod.local`

## 使用方法

### 1. 查看默认账户信息

```bash
curl -X GET "http://localhost:8000/api/auth/admin-info"
```

### 2. 使用默认账户登录

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin&password=admin123"
```

### 3. 获取用户信息

```bash
curl -X GET "http://localhost:8000/api/auth/me" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. 修改管理员信息

```bash
curl -X PUT "http://localhost:8000/api/auth/me" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -d '{
       "full_name": "系统管理员",
       "bio": "TgGod系统管理员"
     }'
```

## 安全建议

1. **立即修改密码**: 首次登录后，强烈建议立即修改默认密码
2. **修改用户名**: 建议修改默认用户名以提高安全性
3. **配置环境变量**: 在生产环境中，通过环境变量自定义默认账户信息
4. **删除默认账户**: 创建其他管理员账户后，可以删除默认账户

## 环境变量配置

可以通过以下环境变量自定义默认管理员账户：

```bash
# 默认管理员账户配置
DEFAULT_ADMIN_USERNAME=your_admin_username
DEFAULT_ADMIN_PASSWORD=your_secure_password
DEFAULT_ADMIN_EMAIL=your_admin@example.com
```

## 重要提示

⚠️ **安全警告**：默认账户仅用于系统初始化，请在生产环境中务必修改默认密码或禁用默认账户！

## 故障排除

如果遇到以下问题：

1. **默认账户创建失败**: 检查数据库连接和权限
2. **登录失败**: 确认用户名和密码是否正确
3. **权限不足**: 确认账户具有超级用户权限

## 技术实现

系统在启动时会自动检查是否存在超级用户，如果不存在则创建默认管理员账户。相关代码位于：

- 配置文件: `backend/app/config.py`
- 用户服务: `backend/app/services/user_service.py`
- 启动脚本: `backend/app/main.py`