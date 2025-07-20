# Task Completion Checklist

## After Code Changes
1. **Database Migration** (if models changed):
   ```bash
   alembic revision --autogenerate -m "description"
   alembic upgrade head
   ```

2. **Testing**:
   ```bash
   python test_system.py
   python check_database.py
   ```

3. **Verification**:
   ```bash
   python production_verify.py
   ```

## For Media-Related Changes
1. Test media downloader:
   ```bash
   python test_media_downloader.py
   ```

2. Verify Telegram configuration:
   ```bash
   python check_telegram_config.py
   ```

## Before Deployment
1. Run all tests
2. Check database schema consistency
3. Verify Telegram API connectivity
4. Test WebSocket functionality
5. Review error logs and handling

## Git Workflow
- Commit with descriptive messages
- Include migration files if database schema changed
- Tag releases appropriately