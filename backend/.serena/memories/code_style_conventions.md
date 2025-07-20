# Code Style and Conventions

## General Style
- Python code follows PEP 8 standards
- SQLAlchemy models use descriptive field names
- Chinese comments for field descriptions
- Consistent naming patterns

## Database Conventions
- Table names use underscores: `telegram_messages`, `telegram_groups`
- Foreign key relationships clearly defined
- Timestamps with timezone support: `DateTime(timezone=True)`
- Default values and constraints properly set

## Model Structure
- Base class inheritance from `Base`
- Relationship definitions with `back_populates`
- Cascade operations defined: `cascade="all, delete-orphan"`
- Composite indexes where needed

## Field Naming Patterns
- Media fields prefixed with `media_`: `media_type`, `media_path`, etc.
- Boolean fields use `is_` prefix: `is_active`, `is_pinned`
- Timestamp fields: `created_at`, `updated_at`, `edit_date`
- Foreign keys end with `_id`: `group_id`, `sender_id`

## Import Organization
- SQLAlchemy imports first
- Local imports using relative paths: `from ..database import Base`

## Documentation
- Chinese comments for field descriptions
- English for code structure and relationships
- Comprehensive field documentation in model definitions