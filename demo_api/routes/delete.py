"""Delete (DELETE) endpoints for Demo API."""
from fastapi import APIRouter, HTTPException, Response
from demo_api.models import items_db

router = APIRouter()


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: int):
    """
    Delete a specific item by ID.

    Args:
        item_id: The ID of the item to delete

    Returns:
        Response: 204 No Content on success

    Raises:
        HTTPException: 404 if item not found
    """
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail=f"Item with id {item_id} not found")

    del items_db[item_id]
    return Response(status_code=204)
