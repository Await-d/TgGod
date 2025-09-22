# TgGod - Telegram Smart Media Download Management System

<div align="center">

[![GitHub stars](https://img.shields.io/github/stars/Await-d/TgGod?style=flat-square)](https://github.com/Await-d/TgGod/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/Await-d/TgGod?style=flat-square)](https://github.com/Await-d/TgGod/issues)
[![Docker Pulls](https://img.shields.io/docker/pulls/await2719/tggod?style=flat-square)](https://hub.docker.com/r/await2719/tggod)
[![License](https://img.shields.io/github/license/Await-d/TgGod?style=flat-square)](LICENSE)

🚀 **Rule-based Telegram Group Media Intelligent Download System**

English | [简体中文](README.md)

</div>

---

## ✨ Introduction

TgGod is a powerful Telegram group media download management system that helps users efficiently manage and archive media content from Telegram groups through intelligent rule filtering and automated downloads. Built with modern technology stack, it provides an intuitive web interface and comprehensive API support.

### 🎯 Key Features

- **🤖 Smart Filtering** - Multi-dimensional rule engine for precise content filtering
- **⚡ High Performance** - Concurrent downloads, resume support, speed optimization
- **📱 Responsive Design** - Perfect adaptation for desktop and mobile devices
- **🔔 Real-time Notifications** - WebSocket push for instant progress updates
- **🐳 Containerized Deployment** - One-click deployment, ready out of the box
- **🔐 Secure & Reliable** - Encrypted data storage, secure session management

## 🚀 Features

### Core Features
- **🔍 Smart Rule Filtering**
  - Multi-dimensional filtering: keywords, regex, media types, file size
  - Time range selection: precise to the second
  - Sender filtering: support for username and user ID
  - Combined rules: AND/OR logic for complex filtering needs

- **📥 Efficient Download Management**
  - Batch downloads: one-click download all matching media
  - Resume support: automatic recovery from network interruptions
  - Concurrency control: smart scheduling to avoid rate limits
  - Deduplication: automatic duplicate file detection

- **📊 Real-time Monitoring Dashboard**
  - Live download progress display
  - System resource monitoring (CPU, memory, disk)
  - Visual task queue
  - Historical data statistics

- **🔔 Smart Notification System**
  - WebSocket real-time push
  - Multi-level log classification
  - Automatic exception alerts
  - Download completion notifications

- **🎨 Modern User Interface**
  - Responsive design for all devices
  - Dark/Light theme switching
  - Drag-and-drop operations
  - Internationalization (Chinese/English)

## Project Structure

```
TgGod/
├── backend/          # Python backend
├── frontend/         # React frontend
├── docker/           # Docker configuration
├── docs/             # Documentation
└── README.md
```

## Technology Stack

- **Frontend**: React, TypeScript, Ant Design, Socket.io
- **Backend**: Python, FastAPI, Telethon, SQLAlchemy
- **Database**: SQLite (externally mounted)
- **Deployment**: Docker (single-service architecture)

## Quick Start

### 🚀 Method 1: Using Pre-built Docker Image (Recommended)

```bash
# 1. Create project directory
mkdir tggod && cd tggod

# 2. Download configuration files
wget https://raw.githubusercontent.com/Await-d/TgGod/master/docker-compose.yml
wget https://raw.githubusercontent.com/Await-d/TgGod/master/.env.example

# 3. Configure environment variables
cp .env.example .env
# Edit .env file with your Telegram API credentials

# 4. Start services (auto-pulls latest image)
docker-compose up -d

# 5. Access application
# Web Interface: http://localhost
# API Docs: http://localhost/docs
```

### 🔧 Method 2: Build from Source

```bash
# 1. Clone repository
git clone https://github.com/Await-d/TgGod.git
cd TgGod

# 2. Configure environment variables
cp .env.example .env
# Edit .env file with Telegram API credentials

# 3. Start services
docker-compose up -d --build

# 4. Access application
# Frontend: http://localhost
# API: http://localhost/docs
```

### ⚡ Method 3: Quick Start Script

```bash
git clone https://github.com/Await-d/TgGod.git
cd TgGod
./scripts/deployment/quick-start.sh
```

## Service Architecture

**Single Service Architecture** - Frontend + Backend + Database combined in one container:
- **Port**: 80 (unified entry)
- **Frontend**: Nginx serving static files
- **Backend**: FastAPI running on internal port 8000
- **Database**: SQLite externally mounted for persistence
- **Files**: Media, logs, session files externally mounted

## Data Persistence

All important data is mounted to external directories:
```
./data/              # Database files
./media/             # Media files
./logs/              # Log files
./telegram_sessions/ # Telegram sessions
```

## 📸 Screenshots

<details>
<summary>Click to view screenshots</summary>

### Dashboard
![Dashboard](docs/images/dashboard.png)

### Rules Management
![Rules](docs/images/rules.png)

### Download Tasks
![Tasks](docs/images/tasks.png)

### Real-time Logs
![Logs](docs/images/logs.png)

</details>

## 🎯 Use Cases

- **📚 Content Archiving** - Save important group history and media
- **🎬 Media Collection** - Auto-collect specific types of images and videos
- **📰 Information Monitoring** - Monitor messages with specific keywords
- **💾 Data Backup** - Regular backup of group content
- **🔍 Content Filtering** - Extract valuable information from massive messages

## 🐳 Docker Deployment

### Pre-built Images (Recommended)

We provide official Docker images with multi-architecture support:

```bash
# Pull latest image
docker pull await2719/tggod:latest

# Or specify version
docker pull await2719/tggod:v1.0.0

# View all available versions
docker search await2719/tggod
```

**Supported Architectures:**
- `linux/amd64` (x86_64)
- `linux/arm64` (ARM64/Apple Silicon)

### Complete Deployment Example

#### 1. Using docker-compose (Recommended)

```yaml
# docker-compose.yml
services:
  tggod:
    image: await2719/tggod:latest
    container_name: tggod
    ports:
      - "80:80"
    volumes:
      - ./data:/app/data
      - ./media:/app/media
      - ./logs:/app/logs
      - ./telegram_sessions:/app/telegram_sessions
    environment:
      - DATABASE_URL=sqlite:////app/data/tggod.db
      - TELEGRAM_API_ID=${TELEGRAM_API_ID}
      - TELEGRAM_API_HASH=${TELEGRAM_API_HASH}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - SECRET_KEY=${SECRET_KEY}
      - MEDIA_ROOT=/app/media
      - LOG_FILE=/app/logs/app.log
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

#### 2. Using docker run

```bash
# Create data directories
mkdir -p data media logs telegram_sessions

# Run container
docker run -d \
  --name tggod \
  -p 80:80 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/media:/app/media \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/telegram_sessions:/app/telegram_sessions \
  -e TELEGRAM_API_ID=your_api_id \
  -e TELEGRAM_API_HASH=your_api_hash \
  -e TELEGRAM_BOT_TOKEN=your_bot_token \
  -e SECRET_KEY=your_secret_key \
  await2719/tggod:latest
```

### 🔧 Environment Variables

Create `.env` file:

```bash
# Telegram API Configuration (Required)
# Get from https://my.telegram.org/apps
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash

# Telegram Bot Token (Required)
# Get from @BotFather
TELEGRAM_BOT_TOKEN=your_bot_token

# Security Configuration (Required)
# Generate random strings for keys
SECRET_KEY=your_secret_key_32_chars_long
JWT_SECRET_KEY=your_jwt_secret_32_chars_long

# Optional Configuration (with defaults)
DATABASE_URL=sqlite:////app/data/tggod.db
MEDIA_ROOT=/app/media
LOG_FILE=/app/logs/app.log
```

**Getting Telegram API Credentials:**

1. Visit https://my.telegram.org/apps
2. Login to your Telegram account
3. Create new app to get `API_ID` and `API_HASH`
4. Contact @BotFather to create bot and get `BOT_TOKEN`

**Generate Security Keys:**

```bash
# Generate random key
openssl rand -hex 32
# Or using Python
python -c "import secrets; print(secrets.token_hex(32))"
```

### 📁 Data Persistence

Important data directories:

| Directory | Purpose | Importance |
|-----------|---------|------------|
| `./data/` | SQLite database files | ⭐⭐⭐ Must backup |
| `./media/` | Downloaded media files | ⭐⭐⭐ Important data |
| `./logs/` | Application logs | ⭐⭐ For debugging |
| `./telegram_sessions/` | Telegram session files | ⭐⭐⭐ Avoid re-auth |

### 🚀 Quick Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Update image
docker-compose pull && docker-compose up -d
```

### 🔍 Health Check

```bash
# Check service status
curl http://localhost/health

# View container status
docker ps

# Enter container for debugging
docker exec -it tggod bash
```

### Local Development

```bash
# Backend development
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend development
cd frontend
pnpm install
pnpm dev
```

### 🚨 Troubleshooting

**Common Issues:**

1. **Port Conflicts**
   ```bash
   # Check port usage
   netstat -tlnp | grep :80
   # Or use lsof
   lsof -i :80

   # Change port mapping
   # Edit docker-compose.yml
   ports:
     - "8080:80"  # Use port 8080 instead
   ```

2. **Permission Issues**
   ```bash
   # Fix directory permissions
   sudo chown -R $USER:$USER data media logs telegram_sessions

   # Ensure directories exist
   mkdir -p data media logs telegram_sessions
   ```

3. **Database Errors**
   ```bash
   # Check database status
   docker exec -it tggod ls -la /app/data/

   # Reset database (use with caution)
   docker-compose down
   rm -rf data/tggod.db
   docker-compose up -d
   ```

4. **Telegram Authentication Failed**
   ```bash
   # Check API credentials
   docker logs tggod | grep -i telegram

   # Re-authenticate (delete session files)
   rm -rf telegram_sessions/*
   docker-compose restart
   ```

5. **Container Startup Failed**
   ```bash
   # View detailed logs
   docker-compose logs tggod

   # Check container status
   docker ps -a

   # Debug inside container
   docker exec -it tggod bash
   ```

## 🔄 Automated Deployment

The project has GitHub Actions automated pipeline configured:

- **Auto Build**: Auto-builds on push to `master` branch
- **Multi-arch Images**: Supports `linux/amd64` and `linux/arm64`
- **Version Management**: Automatic version numbering and changelog
- **Docker Hub**: Auto-pushes to `await2719/tggod`

**Pull Latest Version:**
```bash
docker-compose pull && docker-compose up -d
```

## 📚 Documentation

- [Deployment Guide](CLAUDE.md)
- [API Documentation](http://localhost/docs) (after startup)
- [Development Guide](frontend/CLAUDE.md)
- [Troubleshooting](docs/)

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

## 🙏 Acknowledgments

- Thanks to [Telethon](https://github.com/LonamiWebs/Telethon) for powerful Telegram API
- Thanks to [FastAPI](https://github.com/tiangolo/fastapi) for high-performance web framework
- Thanks to all contributors for their support

## 📞 Contact

- **Issues**: [GitHub Issues](https://github.com/Await-d/TgGod/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Await-d/TgGod/discussions)

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Await-d/TgGod&type=Date)](https://star-history.com/#Await-d/TgGod&Date)

<div align="center">

**If this project helps you, please give us a ⭐ Star!**

[![GitHub Star](https://img.shields.io/github/stars/Await-d/TgGod?style=social)](https://github.com/Await-d/TgGod)

</div>