# Suggested Development Commands

## Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python init_database.py

# Setup Telegram API credentials
bash setup_telegram_api.sh
python set_telegram_config.py
```

## Running the Application
```bash
# Development server
python start_app.py

# Production server
python production_start.py

# Check system status
python production_verify.py
```

## Database Management
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Check database status
python check_database.py
```

## Testing
```bash
# Test database initialization
python test_db_init.py

# Test system functionality
python test_system.py

# Test Telegram groups
python test_telegram_groups.py

# Test media downloader
python test_media_downloader.py
```

## Maintenance
```bash
# Check Telegram configuration
python check_telegram_config.py

# 修复脚本已归档，如需使用：
# python scripts/archive/force_fix_forwarded_columns.py
# python scripts/archive/fix_production.py
```

## System Commands (Linux)
- `ls` - list directory contents
- `cd` - change directory  
- `grep` - search text patterns
- `find` - find files
- `git` - version control
- `docker` - containerization (Dockerfile present)