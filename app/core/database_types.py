"""
Database-agnostic type definitions for SQLAlchemy.
Provides portable types that work with both PostgreSQL and SQLite.
"""
import json
from sqlalchemy import TypeDecorator, Text, String
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.types import JSON
import uuid


class PortableJSON(TypeDecorator):
    """JSON type that works with both PostgreSQL (JSONB) and SQLite (TEXT)."""
    
    impl = Text
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(Text())
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == 'postgresql':
            return value
        else:
            return json.dumps(value)
    
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == 'postgresql':
            return value
        else:
            return json.loads(value)


class PortableUUID(TypeDecorator):
    """UUID type that works with both PostgreSQL (UUID) and SQLite (STRING)."""
    
    impl = String(36)
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == 'postgresql':
            return value
        else:
            return str(value)
    
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == 'postgresql':
            return value
        else:
            return uuid.UUID(value)


class PortableArray(TypeDecorator):
    """Array type that works with both PostgreSQL (ARRAY) and SQLite (JSON)."""
    
    impl = Text
    cache_ok = True
    
    def __init__(self, item_type=String):
        self.item_type = item_type
        super().__init__()
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(ARRAY(self.item_type))
        else:
            return dialect.type_descriptor(Text())
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == 'postgresql':
            return value
        else:
            return json.dumps(value)
    
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == 'postgresql':
            return value
        else:
            return json.loads(value)


# Type aliases for backward compatibility
JSON_TYPE = PortableJSON
UUID_TYPE = PortableUUID
ARRAY_TYPE = PortableArray