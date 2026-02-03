"""Create endpoint for Demo API."""
from fastapi import APIRouter, status
from demo_api.models import ItemCreate, Item, items_db, next_id

router = APIRouter()


@router.post("/items", response_model=Item, status_code=status.HTTP_201_CREATED)
def create_item(item: ItemCreate) -> Item:
    """
    Create a new item.

    Args:
        item: Item data to create

    Returns:
        Created item with ID
    """
    global next_id

    # Create new item with ID
    item_id = next_id
    item_dict = item.model_dump()
    items_db[item_id] = item_dict

    # Increment ID counter
    next_id += 1

    # Return created item
    return Item(id=item_id, **item_dict)
