import re
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator, Field
import string

#описываем ожидаемые входящие данные (HTTP запроса) и автоматически проверяем
class UserRegister(BaseModel):
    login: str
    password: str
    #проверяем соответствие требованиям 
    @field_validator("login")
    @classmethod
    def validate_login(cls, value: str) -> str:
        if not 3 <= len(value) <= 32:
            raise ValueError("Логин должен содержать от 3 до 32 символов")

        if not re.fullmatch(r"[A-Za-z0-9._-]+", value):
            raise ValueError(
                "Логин может содержать только латинские буквы, "
                "цифры, точку, дефис и нижнее подчёркивание"
            )

        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
            if (
                len(value) < 8
                or not re.search(r"[A-Z]", value)
                or not re.search(r"[a-z]", value)
                or not re.search(r"[0-9]", value)
                # стандартные ASCII-знаки пунктуации
                or not any(char in string.punctuation for char in value)
            ):
                raise ValueError(
                    "Пароль должен содержать не менее 8 символов, "
                    "заглавную и строчную латинские буквы, "
                    "цифру и специальный символ"
                )

            return value

#схема ответа сервера 
#сервер возвращает инфу о созданном пользователе (без пароля и хэша) 
class UserCreated(BaseModel):
    id: int
    login: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

#схема авторизации
class UserLogin(BaseModel):
    login: str
    password: str

# схема ответа
class Token(BaseModel):
     access_token: str
     token_type: str  = "bearer" #Тип токена — bearer

#данные, которые frontend отправляет для создания документа
class ResourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=32)
    content: str = Field(min_length=1)

#данные, которые backend возвращает после создания
class ResourceOut(BaseModel):
    id: int
    name: str
    content: str
    owner_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

#схема (запроса) для выдачи прав на ресурс владельцем
class PermissionGrant(BaseModel):
    user_login: str
    can_read: bool
    can_update: bool
    can_delete: bool

#схема ответа, что сервер действительно сохранил в базе данных
class PermissionOut(BaseModel):
    resource_id: int
    user_id: int
    can_read: bool
    can_update: bool
    can_delete: bool

    model_config = ConfigDict(from_attributes=True)