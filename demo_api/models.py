"""Pydantic models for Demo API."""
from pydantic import BaseModel
from typing import Optional


class ItemBase(BaseModel):
    """Base model for Item."""
    name: str
    description: Optional[str] = None
    price: float
    quantity: int = 0


class ItemCreate(ItemBase):
    """Model for creating an Item."""
    pass


class ItemUpdate(BaseModel):
    """Model for updating an Item."""
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None


class Item(ItemBase):
    """Model for Item with ID."""
    id: int

    class Config:
        from_attributes = True


# In-memory storage (shared across routes)
items_db: dict[int, dict] = {}
next_id: int = 1
