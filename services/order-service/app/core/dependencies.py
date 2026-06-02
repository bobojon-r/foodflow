import enum

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://auth-service:8001/api/v1/auth/login")


class UserRole(str, enum.Enum):
    CUSTOMER = "customer"
    RESTAURANT_OWNER = "restaurant_owner"
    COURIER = "courier"
    ADMIN = "admin"


class TokenUser:
    def __init__(self, user_id: int, role: UserRole) -> None:
        self.id = user_id
        self.role = role


def _decode(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return {}


async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenUser:
    payload = _decode(token)
    user_id = payload.get("sub")
    role = payload.get("role")
    if not user_id or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenUser(user_id=int(user_id), role=UserRole(role))


async def require_restaurant_owner(current_user: TokenUser = Depends(get_current_user)) -> TokenUser:
    if current_user.role not in (UserRole.RESTAURANT_OWNER, UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Restaurant owner access required")
    return current_user
