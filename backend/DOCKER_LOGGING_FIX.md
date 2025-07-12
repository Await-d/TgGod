# Docker 日志输出问题修复指南

## 问题原因
1. Python 脚本执行后改变了 stdout/stderr 重定向
2. 输出缓冲导致日志不能实时显示
3. uvicorn 继承了被修改的输出流配置

## 已实施的修复措施

### 1. 修改 production_start.py
- 添加 `PYTHONUNBUFFERED=1` 环境变量
- 设置 `sys.stdout.reconfigure(line_buffering=True)`
- 强制刷新输出：`sys.stdout.flush()`
- 恢复原始输出流给 uvicorn
- 禁用颜色输出避免控制字符干扰

### 2. Docker 运行配置建议
在 Dockerfile 或运行命令中添加：

```dockerfile
# 在 Dockerfile 中添加
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8

# 或在 docker run 命令中添加
docker run -e PYTHONUNBUFFERED=1 -e PYTHONIOENCODING=UTF-8 tggod:latest
```

### 3. Docker Compose 配置
```yaml
environment:
  - PYTHONUNBUFFERED=1
  - PYTHONIOENCODING=UTF-8
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

## 验证修复效果
重新部署后，应该能看到连续的日志输出：
1. 启动阶段的数据库检查日志
2. uvicorn 启动日志
3. API 请求处理日志

## 预防措施
1. 避免在脚本中直接重定向 sys.stdout
2. 使用 `flush=True` 参数确保输出立即显示
3. 在容器中禁用 ANSI 颜色代码
4. 设置合适的日志级别和格式