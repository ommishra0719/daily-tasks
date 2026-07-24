import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sessions = relationship(
        "ChatSession", back_populates="user", cascade="all, delete-orphan"
    )


class ChatSession(Base):
    """
    One conversation. Stores the resolved system-prompt TEXT as a snapshot
    at creation time (not just the prompt_name) so that if the named prompt
    is edited or removed later, existing sessions keep behaving exactly as
    they did when they were created -- and we always know, for any given
    session, precisely what system prompt shaped its behaviour.
    """

    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, default=_uuid, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    prompt_name = Column(String, nullable=False)
    system_prompt = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="sessions")
    messages = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=False, index=True)

    role = Column(String, nullable=False)  # "user" | "model"
    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")
