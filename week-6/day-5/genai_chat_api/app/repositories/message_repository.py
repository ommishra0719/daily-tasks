from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.models import Message


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self, session_id: str, role: str, content: str, token_count: int = 0
    ) -> Message:
        message = Message(
            session_id=session_id,
            role=role,
            content=content,
            token_count=token_count,
        )
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def list_for_session(self, session_id: str) -> list[Message]:
        """Full history, oldest first -- used by the GET history endpoint."""
        result = await self.session.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc(), Message.id.asc())
        )
        return list(result.scalars().all())

    async def last_n_for_session(self, session_id: str, n: int) -> list[Message]:
        """
        Most recent `n` messages, returned in chronological (oldest-first)
        order so they can be fed straight into the model as context. This
        is the "sliding window" that keeps the prompt bounded regardless of
        how long the conversation has actually run.
        """
        result = await self.session.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(n)
        )
        rows = list(result.scalars().all())
        rows.reverse()
        return rows

    async def clear_for_session(self, session_id: str) -> None:
        await self.session.execute(
            sa_delete(Message).where(Message.session_id == session_id)
        )
        await self.session.commit()
