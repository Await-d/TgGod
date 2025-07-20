# Telegram Data Models

## Core Models Location
File: `/app/models/telegram.py`

## TelegramGroup Model
Table: `telegram_groups`
- Basic group information (id, telegram_id, title, username, description)
- Member count and status tracking
- Relationships to messages, rules, and download tasks

## TelegramMessage Model
Table: `telegram_messages`

### Media-Related Fields (Key Focus)
- `media_type`: String(50) - photo, video, document, audio, voice, sticker
- `media_path`: String(500) - Local file path (only exists after download)
- `media_size`: BigInteger - File size in bytes
- `media_filename`: String(255) - Original filename
- `media_file_id`: String(255) - Telegram file ID (for download)
- `media_file_unique_id`: String(255) - Telegram unique file ID
- `media_downloaded`: Boolean - Whether downloaded to local storage
- `media_download_url`: String(500) - Telegram download link (temporary)
- `media_download_error`: Text - Download failure error messages
- `media_thumbnail_path`: String(500) - Thumbnail image path

### Other Important Fields
- Message content (id, message_id, text, date)
- Sender information (sender_id, sender_username, sender_name)
- Forward information (is_forwarded, forwarded_from, etc.)
- Interaction data (view_count, reactions, mentions)
- Advanced features (reply_to_message_id, is_pinned, hashtags, urls)