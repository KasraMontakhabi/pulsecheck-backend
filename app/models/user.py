from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "user"

    # Custom fields
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)

    # Relationship
    monitors = relationship("Monitor", back_populates="user")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()