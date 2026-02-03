"""Read (GET) endpoints for Demo API."""
from fastapi import APIRouter, HTTPException
from typing import List
from demo_api.models import Item, items_db

router = APIRouter()


@router.get("/items", response_model=List[Item])
async def get_all_items():
    """
    Get all items from the database.

    Returns:
        List[Item]: List of all items
    """
    return [
        Item(id=item_id, **item_data)
        for item_id, item_data in items_db.items()
    ]


@router.get("/items/{item_id}", response_model=Item)
async def get_item_by_id(item_id: int):
    """
    Get a specific item by ID.

    Args:
        item_id: The ID of the item to retrieve

    Returns:
        Item: The requested item

    Raises:
        HTTPException: 404 if item not found
    """
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail=f"Item with id {item_id} not found")

    item_data = items_db[item_id]
    return Item(id=item_id, **item_data)
