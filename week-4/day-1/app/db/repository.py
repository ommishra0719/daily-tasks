from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from db.models import User

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalars().first()

    async def create(self, email: str, hashed_password: str) -> User:
        db_user = User(email=email, hashed_password=hashed_password)
        self.session.add(db_user)
        
        await self.session.commit()
        await self.session.refresh(db_user) # Needed to get the DB-generated ID and timestamps
        
        return db_user