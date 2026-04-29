from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

import models
from database import get_db

SECRET_KEY = "clave_secreta_academica_cambiar_en_produccion"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verificar_password(password_plano, password_hash):
    return pwd_context.verify(password_plano, password_hash)


def generar_hash_password(password):
    return pwd_context.hash(password)


def crear_token_acceso(data: dict, expires_delta: Optional[timedelta] = None):
    datos = data.copy()

    expire = datetime.utcnow() + (
        expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    datos.update({"exp": expire})
    return jwt.encode(datos, SECRET_KEY, algorithm=ALGORITHM)


def obtener_usuario_actual(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credenciales_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id: int = int(payload.get("sub"))
        if usuario_id is None:
            raise credenciales_error
    except JWTError:
        raise credenciales_error

    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()

    if usuario is None:
        raise credenciales_error

    return usuario


def exigir_roles(*roles_permitidos):
    def validador(usuario: models.Usuario = Depends(obtener_usuario_actual)):
        if usuario.rol not in roles_permitidos:
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para realizar esta acción"
            )
        return usuario

    return validador