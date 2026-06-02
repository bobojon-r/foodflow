from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RestaurantCreate(BaseModel):
    name: str
    description: str | None = None
    address: str


class RestaurantUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    address: str | None = None
    is_active: bool | None = None


class RestaurantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    name: str
    description: str | None
    address: str
    is_active: bool
    created_at: datetime
