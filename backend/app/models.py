from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func, ForeignKey, Boolean, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

#атрибут класса = столбец таблицы
#экземпляр класса = конкретная запись в таблице

#пользователи
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer, #тип столбца
        primary_key=True, 
        index=True #создается индекс
    )

    login: Mapped[str] = mapped_column(
        String(32),
        unique=True, #логины не могут повторяться
        nullable=False #значение обязательно, не пусто
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), #дата и время с учетом часового пояса
        server_default=func.now(),
        nullable=False
    )


#описание ресурса 
class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(
        Integer, 
        primary_key=True, 
        index=True
    )

    name: Mapped[str] = mapped_column(
        String(32),
        nullable=False
    )
#содержимое
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    owner_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("users.id"), #внешний ключ связывающий поле с ID юзера в таблице users
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )

#разрешения конкретного пользователя на конкретный ресурс
class ResourcePermission(Base):
    __tablename__ = "resource_permissions"
    #должны быть уникальные пары "resource_id", "user_id"
    __table_args__ = (
    UniqueConstraint("resource_id", "user_id"),
)

    id: Mapped[int] = mapped_column(
        Integer, 
        primary_key=True, 
        index=True
    )

    resource_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("resources.id", ondelete="CASCADE"), #если удаляется ресурс, то удаляем и все заиси, связанные с ним 
        nullable=False
    )

    user_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("users.id"),
        nullable=False 
    )

    can_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False 
    )

    can_update: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False 
    )
    
    can_delete: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False
    )