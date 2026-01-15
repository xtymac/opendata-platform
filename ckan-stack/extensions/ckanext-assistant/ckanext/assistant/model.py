"""Database models for assistant conversations."""
import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Table, UnicodeText
from sqlalchemy.orm import relationship
from ckan.model import meta, core, types, domain_object


conversation_table = Table(
    'assistant_conversation',
    meta.metadata,
    Column('id', String(36), primary_key=True, default=types.make_uuid),
    Column('user_id', String(36), ForeignKey('user.id'), nullable=False),
    Column('title', UnicodeText, nullable=False),
    Column('created_at', DateTime, default=datetime.datetime.utcnow),
    Column('updated_at', DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow),
)


message_table = Table(
    'assistant_message',
    meta.metadata,
    Column('id', String(36), primary_key=True, default=types.make_uuid),
    Column('conversation_id', String(36), ForeignKey('assistant_conversation.id', ondelete='CASCADE'), nullable=False),
    Column('role', String(20), nullable=False),  # 'user' or 'assistant'
    Column('content', Text, nullable=False),
    Column('sources', Text, nullable=True),  # JSON array of source URLs
    Column('created_at', DateTime, default=datetime.datetime.utcnow),
)


class Conversation(domain_object.DomainObject):
    """Represents a conversation thread."""

    @classmethod
    def get(cls, conversation_id: str) -> Optional['Conversation']:
        """Get conversation by ID."""
        return meta.Session.query(cls).filter_by(id=conversation_id).first()

    @classmethod
    def get_for_user(cls, user_id: str, limit: int = 50) -> List['Conversation']:
        """Get all conversations for a user."""
        return (
            meta.Session.query(cls)
            .filter_by(user_id=user_id)
            .order_by(cls.updated_at.desc())
            .limit(limit)
            .all()
        )

    @classmethod
    def create(cls, user_id: str, title: str) -> 'Conversation':
        """Create a new conversation."""
        conv = cls()
        conv.id = types.make_uuid()
        conv.user_id = user_id
        conv.title = title
        conv.created_at = datetime.datetime.utcnow()
        conv.updated_at = datetime.datetime.utcnow()
        meta.Session.add(conv)
        meta.Session.commit()
        return conv

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Message(domain_object.DomainObject):
    """Represents a message in a conversation."""

    @classmethod
    def get_for_conversation(cls, conversation_id: str) -> List['Message']:
        """Get all messages for a conversation."""
        return (
            meta.Session.query(cls)
            .filter_by(conversation_id=conversation_id)
            .order_by(cls.created_at.asc())
            .all()
        )

    @classmethod
    def create(cls, conversation_id: str, role: str, content: str, sources: Optional[List[str]] = None) -> 'Message':
        """Create a new message."""
        import json

        msg = cls()
        msg.id = types.make_uuid()
        msg.conversation_id = conversation_id
        msg.role = role
        msg.content = content
        msg.sources = json.dumps(sources) if sources else None
        msg.created_at = datetime.datetime.utcnow()
        meta.Session.add(msg)
        meta.Session.commit()
        return msg

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        import json

        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'role': self.role,
            'content': self.content,
            'sources': json.loads(self.sources) if self.sources else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# Map tables to classes
meta.mapper(Conversation, conversation_table)
meta.mapper(Message, message_table)


def init_tables():
    """Create tables if they don't exist."""
    from ckan.model import Session

    engine = Session.bind
    if engine is None:
        return

    if not conversation_table.exists(engine):
        conversation_table.create(engine)
    if not message_table.exists(engine):
        message_table.create(engine)
