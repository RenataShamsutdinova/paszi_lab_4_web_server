import logging
#логгирование
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

#подключаем зависимости , возврат HTTP-ошибки и набор HTTP-статусов
from fastapi import FastAPI, Depends, HTTPException, status 
# используем методы обьекта Session — тип объекта, через который мы работаем с базой данных
from sqlalchemy.orm import Session
# ошибка нарушения ограничений БД
from sqlalchemy.exc import IntegrityError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_

from app.config import settings
from jose import jwt
from jose.exceptions import JWTError

#ранее созданные файлы
from app.database import get_db
from app.models import User, Resource, ResourcePermission
from app.schemas import UserRegister, UserCreated, UserLogin, Token, ResourceCreate, ResourceOut, PermissionGrant, PermissionOut
from app.security import hash_password, verify_password, create_access_token

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials 

#создаение приложения
app = FastAPI(
    title="Document Manager API",
    description="API для регистрации пользователей и управления доступом",
)

#настройка логирования приложения -> чтобы записывать события с датой 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

#обработка ошибок валидации входящих данных
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    #записываем только тип ошибки и расположение поля
    #значения полей, в том числе пароли, в лог не попадают
    errors = [
        {
            "field": error.get("loc"),
            "type": error.get("type"),
        }
        for error in exc.errors()
    ]

    logger.error(
        "Ошибка валидации: method=%s path=%s errors=%s",
        request.method,
        request.url.path,
        errors,
    )

    return JSONResponse(
        status_code=422,
        content={
            "detail": [
                {
                    "loc": error.get("loc"),
                    "msg": error.get("msg"),
                    "type": error.get("type"),
                }
                for error in exc.errors()
            ]
        },
    )

#создаём объект класса HTTPBearer (механизм который извлекает JWT token from HTTP-query)
bearer_scheme = HTTPBearer()

#получаем проверяем JWT токен и ищем пользователя в БД
def get_current_user(
    #извлекаем данные авторизации из HTTP-запроса
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    #извекаем только тот атрибут параметра, в котором храниться токен (в другом храниться метод)
    token = credentials.credentials

    try:
        # Проверяем токен и получаем словарь с данными
        check_dict = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный или просроченный токен",
        )

    # Получаем ID пользователя из токена
    try:
        check_user = int(check_dict["sub"])

        if check_user <= 0:
            raise ValueError
        
    except (KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
        )

    # Ищем пользователя в БД
    existing_user = db.query(User).filter(
        User.id == check_user
    ).first()

    if existing_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Учетная запись пользователя недоступна",
        )

    #возвращаем обьект пользователя
    return existing_user


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], #разрешаем запросы с фронтенда(Vite) 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "API is running"}


#обьявление endpoint
@app.post(
    "/api/register",
    response_model=UserCreated, # структура ответа, которую должен получить frontend
    status_code=status.HTTP_201_CREATED,
)
# проверяем получанные данные 
def register_user(
    user_data: UserRegister,
    db: Session = Depends(get_db),
):
    # Проверяем, существует ли пользователь с таким логином
    existing_user = db.query(User).filter(
        User.login == user_data.login
    ).first()

    if existing_user:
        #логируем данные события 
        logger.error("Попытка регистрации с уже существующим логином")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким логином уже существует",
        )

    # Создаем запись пользователя
    new_user = User(
        login=user_data.login,
        password_hash=hash_password(user_data.password),
    )

    # Добавляем объект в сессию SQLAlchem
    db.add(new_user)

    try:
        db.commit()
        db.refresh(new_user)

    #случай, если другой запрос успел зарегистировать такой же логин раньше 
    except IntegrityError:
        db.rollback() #отмена неудачной транзакции
        logger.error("Конфликт уникальности при регистрации пользователя")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким логином уже существует",
        )
    
    logger.info("Успешно зарегистрирован пользователь с ID=%s", new_user.id)
    return new_user
    



@app.post(
    "/api/login", 
    response_model=Token,    
    status_code=status.HTTP_200_OK,
)
#сверяем пароли 
def login_user(
    user_data: UserLogin,
    db: Session = Depends(get_db),
):
    
    existing_user = db.query(User).filter(
        User.login == user_data.login
    ).first()
    # итого получаем Python-объект найденного пользователя

    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )
    
    #сравниваем введенный пароль с хэшем пользователя из таблицы
    cheked = verify_password(user_data.password, existing_user.password_hash)
    if not cheked:
       raise HTTPException(
                   status_code=status.HTTP_401_UNAUTHORIZED,
                   detail="Неверный пароль",
               ) 

    user = {
        "sub": str(existing_user.id)
    }
    logger.info("Успешная авторизация пользователя с ID=%s", existing_user.id)
    access_token = create_access_token(user)

    token_respons={
        "access_token": access_token,
        "token_type": "bearer"
     }
    return token_respons

#возвращаем данные найденного пользователя
@app.get("/api/me")
def get_me(
    current_user: User = Depends(get_current_user), #обьект модели User (depends - выполняется FastAPI)
):
    return {
        "id": current_user.id,
        "login": current_user.login,
    }


@app.post(
    "/api/resources",
    response_model=ResourceOut,    
    status_code=status.HTTP_201_CREATED,
)    
def post_resource(
    entry: ResourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Создаем ресурс 
    new_content = Resource(
        name=entry.name,
        content=entry.content,
        owner_id=current_user.id
    )

    # Добавляем объект в сессию SQLAlchem
    db.add(new_content)
    db.commit()
    db.refresh(new_content) #обновляет Python-объект данными из БД

    return new_content

#возращаем СПИСОК ресурсов, которые доступны текущему пользователю
@app.get(
    "/api/resources",
    response_model=list[ResourceOut]
)
def get_resource(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # находим ID ресурсов, к которым пользователю разрешено чтение
    readable_resource_ids = db.query(
        ResourcePermission.resource_id
    ).filter(
        ResourcePermission.user_id == current_user.id,
        ResourcePermission.can_read.is_(True)
    )

    # получаем собственные ресурсы и ресурсы с разрешением на чтение
    resources = db.query(Resource).filter(
        or_(
            Resource.owner_id == current_user.id,
            Resource.id.in_(readable_resource_ids)
        )
    ).all()

    return resources


@app.post(
    "/api/resources/{resource_id}/permissions",
    response_model=PermissionOut,
    status_code=status.HTTP_200_OK
)
def post_permissions(
    resource_id:int, #FastAPI сам подставит id из URL
    permission_data: PermissionGrant,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)    
):
    #проверяем, существует ли ресурс, к которому обращаются
    resource = db.query(Resource).filter(
        Resource.id==resource_id
    ).first()

    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресурс не найден"
        )
    #проверяем,является ли текущий пользователь владельцем
    if resource.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только владелец может выдавать права"
        ) 

    #проверяем, существует ли пользователь, которому выдаются права     
    target_user = db.query(User).filter(
        User.login == permission_data.user_login
    ).first()

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь с таким логином не найден"
        )

     #проверяем, существует ли запись с такой парой resource_id и user_id
    permission= db.query(ResourcePermission).filter(
        ResourcePermission.resource_id==resource_id,
        ResourcePermission.user_id==target_user.id
    ).first()

    if permission is None:
        #cоздаем запись
        permission = ResourcePermission(
            resource_id=resource_id,
            user_id=target_user.id,
            can_read=permission_data.can_read,
            can_update=permission_data.can_update,
            can_delete=permission_data.can_delete
        )
        db.add(permission)
    else:
        permission.can_read=permission_data.can_read
        permission.can_update=permission_data.can_update
        permission.can_delete=permission_data.can_delete

    db.commit()
    db.refresh(permission)

    return permission

#возращаем конкретный ресурс, если у пользователя есть право на чтение
@app.get("/api/resources/{resource_id}", response_model=ResourceOut)
def get_resource_by_id(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    #находим документ по ID
    resource = db.query(Resource).filter(
        Resource.id == resource_id
    ).first()

    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресурс не найден"
        )

    #если пользователь владелец, разрешаем чтение
    if resource.owner_id == current_user.id:
        return resource

    #ищем разрешение текущего пользователя на этот документ
    permission = db.query(ResourcePermission).filter(
        ResourcePermission.resource_id == resource_id,
        ResourcePermission.user_id == current_user.id
    ).first()

    #проверяем право на чтение
    if permission is None or not permission.can_read:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав на чтение ресурса"
        )

    return resource

# Получаем права текущего пользователя на конкретный ресурс
@app.get(
    "/api/resources/{resource_id}/my-permissions",
    response_model=PermissionOut
)
def get_my_permissions(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    #проверяем, существует ли документ
    resource = db.query(Resource).filter(
        Resource.id == resource_id
    ).first()

    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресурс не найден"
        )

    #владелец обладает всеми правами на свой документ
    if resource.owner_id == current_user.id:
        return {
            "resource_id": resource.id,
            "user_id": current_user.id,
            "can_read": True,
            "can_update": True,
            "can_delete": True
        }

    #ищем права, выданные текущему пользователю
    permission = db.query(ResourcePermission).filter(
        ResourcePermission.resource_id == resource_id,
        ResourcePermission.user_id == current_user.id
    ).first()

    if permission is None or not permission.can_read:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав на чтение ресурса"
        )

    return permission


#изменение докусента (update resource)
@app.put("/api/resources/{resource_id}", response_model=ResourceOut)
def update_resource(
    resource_id: int,
    resource_data: ResourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    #находим документ
    resource = db.query(Resource).filter(
        Resource.id == resource_id
    ).first()

    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресурс не найден"
        )

    #если пользователь не владелец, проверяем его права
    if resource.owner_id != current_user.id:
        permission = db.query(ResourcePermission).filter(
            ResourcePermission.resource_id == resource_id,
            ResourcePermission.user_id == current_user.id
        ).first()

        #реализуем так, что ессли нет прав на чтение то автомтически и на изменение тодже нет (но можно так и не делать)
        if permission is None or not permission.can_update:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав на изменение ресурса"
            )

    #обновляем название и содержимое
    resource.name = resource_data.name
    resource.content = resource_data.content

    #сохраняем изменения
    db.commit()
    db.refresh(resource)

    return resource

#удаление документа
@app.delete("/api/resources/{resource_id}")
def delete_resource(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    resource = db.query(Resource).filter(
        Resource.id == resource_id
    ).first()

    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ресурс не найден"
        )

    #если пользователь не владелец, проверяем его права
    if resource.owner_id != current_user.id:
        permission = db.query(ResourcePermission).filter(
            ResourcePermission.resource_id == resource_id,
            ResourcePermission.user_id == current_user.id
        ).first()

        if permission is None or not permission.can_delete:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав на удаление ресурса"
            )

    #удаляем документ
    db.delete(resource)
    db.commit()

    return {"message": "Ресурс успешно удалён"}


@app.get("/api/resources/{resource_id}/permissions")
def get_resource_permissions(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Находим документ
    resource = db.query(Resource).filter(
        Resource.id == resource_id
    ).first()

    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Документ не найден",
        )

    # Только владелец может просматривать список выданных разрешений
    if resource.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только владелец может просматривать список разрешений",
        )

    # Получаем разрешения и логины пользователей
    permissions = (
        db.query(ResourcePermission, User.login)
        .join(
            User,
            User.id == ResourcePermission.user_id,
        )
        .filter(
            ResourcePermission.resource_id == resource_id
        )
        .order_by(User.login)
        .all()
    )

    # Формируем ответ для frontend
    return [
        {
            "user_id": permission.user_id,
            "user_login": login,
            "can_read": permission.can_read,
            "can_update": permission.can_update,
            "can_delete": permission.can_delete,
        }
        for permission, login in permissions
    ]
