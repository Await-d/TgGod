# 前端Dockerfile
FROM registry.cn-hangzhou.aliyuncs.com/library/node:18-alpine

# 设置工作目录
WORKDIR /app

# 安装依赖项
RUN apk add --no-cache git python3 make g++

# 设置环境变量
ENV NODE_OPTIONS=--max-old-space-size=4096
ENV CI=false

# 配置npm镜像源
RUN npm config set registry https://registry.npmmirror.com

# 安装pnpm
RUN npm install -g pnpm --registry=https://registry.npmmirror.com

# 配置pnpm镜像源和超时
RUN pnpm config set registry https://registry.npmmirror.com
RUN pnpm config set network-timeout 300000

# 复制package文件
COPY package*.json ./
COPY pnpm-lock.yaml ./

# 安装依赖
RUN pnpm install

# 复制源代码
COPY . .

# 构建应用
RUN pnpm build

# 使用nginx提供静态文件
FROM registry.cn-hangzhou.aliyuncs.com/library/nginx:alpine

# 复制构建文件
COPY --from=0 /app/build /usr/share/nginx/html

# 复制nginx配置
COPY nginx.conf /etc/nginx/nginx.conf

# 暴露端口
EXPOSE 80

# 启动nginx
CMD ["nginx", "-g", "daemon off;"]