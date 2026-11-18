
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError

from app.config import settings

from jose import jwt #предоставляет методы кодирования и проверки токенов
from datetime import datetime, timedelta, timezone

password_hasher = PasswordHasher(
    time_cost=settings.argon2_time_cost,
    memory_cost=settings.argon2_memory_cost,
    parallelism=settings.argon2_parallelism,
    type=Type.ID,
)

#возвращаем посчитанный хэш
def hash_password(password: str) -> str:
    return password_hasher.hash(password)

#сравниваем пароль с хэшем из таблицы
def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except VerificationError:
        return False

#создание JWT токена (на вход принимаем словарь с данными пользователя)
def create_access_token(data: dict) -> str:
    #время окончания действия токена
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)

    #в словарь c ID юзера добавляем дату окончания токена 
    to_encode = data.copy()
    to_encode["exp"] = expire

    encoded_jwt = jwt.encode(to_encode, settings.secret_key, settings.algorithm)
    return encoded_jwt