# Docker配置文件

# 后端Dockerfile
FROM python:3.11.8-slim

# 设置工作目录
WORKDIR /app


# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p media logs

# 暴露端口
EXPOSE 8000

# 运行命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]