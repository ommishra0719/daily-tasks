from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.models import ChatSession


class SessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: int, prompt_name: str, system_prompt: str) -> ChatSession:
        chat_session = ChatSession(
            user_id=user_id,
            prompt_name=prompt_name,
            system_prompt=system_prompt,
        )
        self.session.add(chat_session)
        await self.session.commit()
        await self.session.refresh(chat_session)
        return chat_session

    async def get_by_id(self, session_id: str) -> ChatSession | None:
        result = await self.session.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        return result.scalars().first()

    async def list_for_user(self, user_id: int) -> list[ChatSession]:
        result = await self.session.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete(self, chat_session: ChatSession) -> None:
        await self.session.delete(chat_session)
        await self.session.commit()
