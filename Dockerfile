# 多阶段构建：前端构建 + 后端服务合并
FROM node:18-alpine AS frontend-build

# 设置工作目录
WORKDIR /app

# 安装依赖项
RUN apk add --no-cache git python3 make g++

# 设置环境变量
ENV NODE_OPTIONS=--max-old-space-size=4096
ENV CI=false

# 安装pnpm
RUN npm install -g pnpm

# 复制前端package文件
COPY frontend/package*.json ./
COPY frontend/pnpm-lock.yaml ./

# 安装前端依赖
RUN pnpm install

# 复制前端源代码
COPY frontend/ .

# 构建前端应用
RUN pnpm build

# 后端服务阶段
FROM python:3.11.8-slim AS backend

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    nginx \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件
COPY backend/requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端应用代码
COPY backend/ .

# 从前端构建阶段复制构建文件
COPY --from=frontend-build /app/build /usr/share/nginx/html

# 复制nginx配置
COPY nginx.conf /etc/nginx/nginx.conf

# 创建必要的目录
RUN mkdir -p /app/data /app/media /app/logs

# 复制启动脚本
COPY start.sh /start.sh
RUN chmod +x /start.sh

# 暴露端口
EXPOSE 80

# 运行启动脚本
CMD ["/start.sh"]