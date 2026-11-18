from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

#подключаем созданный в config.py обьект settings
from app.config import settings

#engine - основной механизм взаимодействия с БД 
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True, #проверка работоспособности соединения 
)

#создание обьектса - сессии (через которые выполняются операции в бд)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False, #накопленные именения в бд будем отправлять самостоятельно (db.commit()), а не автоматически 
    autocommit=False, # и автоматическое подтверждение изменений тоже отключаем
)

# родительский класс для ORM-моделей
class Base(DeclarativeBase):
    pass

# функция, которая будет предоставлять сессию другим частям приложения
def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()