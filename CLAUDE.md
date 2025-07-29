# CLAUDE.md
在项目根目录下创建一个todo 文件（不存在则创建），你需要先将我们商量好的代办任务添加到todo文件中，每完成一个任务对应的任务标记已完成，这样方便我们实时跟踪开发进度。

合理使用 Task 工具创建多个子代理来提高开发效率，每个子代理负责一个独立的任务，互不干扰，支持并行执行。

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## TgGod - Telegram Group Rule-based Download System

This is a single-service architecture application that combines a React frontend, FastAPI backend, and SQLite database for downloading media from Telegram groups based on customizable rules.

## Development Commands

### Quick Start
```bash
# One-click deployment
./quick-start.sh

# Manual deployment test
./deploy-test.sh
```

### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run database migrations
python fix_database_schema.py
python fix_task_fields.py
```

### Frontend Development
```bash
cd frontend
pnpm install
pnpm dev        # Development server on port 3000
pnpm build      # Production build
pnpm preview    # Preview production build
```

### Docker Deployment
```bash
# Single-service architecture
docker-compose up -d --build
docker-compose logs -f              # View logs
docker-compose down                 # Stop services
docker-compose restart              # Restart services

# Health check
curl http://localhost/health
```

### Testing
```bash
# Test service dependencies
python simple_test.py

# Test service installer
python test_service_installer.py
```

## Architecture Overview

### Single-Service Architecture
The application runs as a single Docker container combining:
- **Frontend**: React app served by Nginx on port 80
- **Backend**: FastAPI server on internal port 8000
- **Database**: SQLite with external volume mounting
- **Static Files**: Media, logs, and Telegram sessions externally mounted

### Core Components

**Backend (`backend/app/`)**
- `main.py`: FastAPI application with lifespan management and service auto-installation
- `api/`: REST API endpoints organized by domain (telegram, rule, media, etc.)
- `services/`: Business logic services including:
  - `service_installer.py`: Auto-installs system dependencies (ffmpeg, fonts, monitoring tools)
  - `service_monitor.py`: Real-time system health monitoring
  - `telegram_service.py`: Telegram client management using Telethon
  - `media_downloader.py`: Handles media file downloads with session management
  - `file_organizer_service.py`: Organizes downloaded files with NFO metadata generation
  - `task_scheduler.py`: Background task management
- `models/`: SQLAlchemy database models
- `websocket/`: Real-time WebSocket communication

**Frontend (`frontend/src/`)**
- React + TypeScript + Ant Design
- Zustand for state management
- Real-time WebSocket integration
- Pages: Dashboard, Groups, Rules, Tasks, Logs, Settings

### Database Schema
SQLite database with external mounting at `./data/tggod.db`. Key tables:
- `telegram_groups`: Managed Telegram groups
- `telegram_messages`: Downloaded messages with metadata
- `filter_rules`: Rule-based filtering configurations
- `download_tasks`: Background download tasks
- `user_settings`: User preferences and configurations

### Service Dependencies
The application automatically installs and monitors system dependencies:
- **FFmpeg**: Video processing and thumbnail generation
- **System fonts**: Text rendering in generated images
- **Python monitoring packages**: psutil, py-cpuinfo for system metrics
- **Media tools**: ImageMagick, ExifTool for advanced processing

## Configuration

### Environment Variables (`.env`)
```bash
# Required Telegram API credentials
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_BOT_TOKEN=your_bot_token

# Security keys (change in production)
SECRET_KEY=your_secret_key
JWT_SECRET_KEY=your_jwt_secret

# Optional database and paths
DATABASE_URL=sqlite:///./data/tggod.db
MEDIA_ROOT=/app/media
LOG_FILE=/app/logs/app.log
```

### Data Persistence
All important data is mounted externally:
- `./data/`: Database files
- `./media/`: Downloaded media files
- `./logs/`: Application logs
- `./telegram_sessions/`: Telegram client sessions

## Development Patterns

### API Design
- RESTful endpoints under `/api/` prefix
- FastAPI with automatic OpenAPI documentation at `/docs`
- WebSocket endpoint at `/ws/{client_id}` for real-time updates
- Service health endpoints at `/api/health/*`

### Service Management
- Application uses modern FastAPI lifespan management (not deprecated on_event)
- Services auto-install dependencies on startup via `service_installer.py`
- Real-time system monitoring via `service_monitor.py`
- All services gracefully handle failures and continue operation

### Database Operations
- SQLAlchemy ORM with session management
- Database schema auto-migration scripts in root directory
- Automatic database health checks on startup
- Support for concurrent operations with proper session handling

### Frontend State Management
- Zustand stores for global state (auth, settings, websocket)
- Real-time updates via WebSocket integration
- Theme system with dark/light mode support
- Responsive design with configurable density settings

## Common Issues and Solutions

### Application Startup
If the application fails to start, check:
1. Environment variables are properly configured in `.env`
2. Required directories exist: `data/`, `media/`, `logs/`, `telegram_sessions/`
3. System dependencies are installed (automatically handled by service installer)
4. Port 80 is not occupied by other services

### Database Issues
- Database migrations run automatically on startup
- If schema issues occur, run migration scripts manually: `python fix_*.py`
- Database health check available at `/api/database/check`

### Service Dependencies
- System dependencies are auto-installed on startup
- Check service status at `/api/health/services`
- Manual installation commands available in service installer logs

## API Endpoints

Key endpoints for development and testing:

### System Health
- `GET /health` - Basic health check
- `GET /api/health/services` - Detailed service health status
- `GET /api/system/resources` - System resource usage
- `POST /api/services/install` - Force service installation

### Core Features
- `/api/telegram/*` - Telegram group management
- `/api/rule/*` - Filter rule configuration
- `/api/media/*` - Media file operations
- `/api/task/*` - Download task management
- `/api/dashboard/*` - Statistics and monitoring

The application includes comprehensive logging, error handling, and automatic dependency management to ensure reliable operation in various deployment environments.