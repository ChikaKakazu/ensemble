"""Update endpoint for Demo API."""
from fastapi import APIRouter, HTTPException, status
from demo_api.models import ItemUpdate, Item, items_db

router = APIRouter()


@router.put("/items/{item_id}", response_model=Item)
def update_item(item_id: int, item_update: ItemUpdate) -> Item:
    """
    Update an existing item.

    Args:
        item_id: ID of the item to update
        item_update: Item data to update (partial update supported)

    Returns:
        Updated item with ID

    Raises:
        HTTPException: 404 if item not found
    """
    # Check if item exists
    if item_id not in items_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found"
        )

    # Get existing item data
    existing_item = items_db[item_id]

    # Update only non-None fields (partial update)
    update_data = item_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        existing_item[field] = value

    # Return updated item
    return Item(id=item_id, **existing_item)
