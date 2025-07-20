# Project Overview

This is a Telegram data collection and management backend system built with FastAPI and SQLAlchemy.

## Purpose
- Collects and stores Telegram messages from groups/channels
- Provides media file download and management capabilities
- Offers API endpoints for data access and rule management
- Supports real-time updates via WebSocket

## Tech Stack
- **Framework**: FastAPI (0.104.1) with uvicorn
- **Database**: SQLAlchemy (2.0.23) with aiosqlite for async operations
- **Telegram API**: Telethon (1.32.1)
- **Migration**: Alembic (1.12.1)
- **Additional**: WebSockets, pandas, pillow for media processing

## Key Components
- `/app/models/` - Database models (Telegram, rules, logs, users)
- `/app/api/` - REST API endpoints
- `/app/services/` - Business logic layer
- `/app/tasks/` - Background tasks (message synchronization)
- `/alembic/` - Database migrations