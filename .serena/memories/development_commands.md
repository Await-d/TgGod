# 开发建议和命令

## 推荐的开发命令
```bash
# 后端开发
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端开发
cd frontend
npm install
npm start

# 数据库迁移
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## 开发注意事项
1. 使用SQLite作为默认数据库，简化部署
2. 所有API接口都需要考虑异步处理
3. WebSocket用于实时日志推送
4. 媒体文件存储在本地./media目录
5. 支持Docker容器化部署

## 测试建议
- 使用pytest进行单元测试
- 使用httpx进行API测试
- WebSocket测试使用websockets库