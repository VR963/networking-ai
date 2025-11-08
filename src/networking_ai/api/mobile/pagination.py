"""
Cursor-based pagination utilities for mobile API.

Cursor-based pagination is more efficient than offset-based for mobile:
- No skipped or duplicate items when data changes
- Better performance for large datasets
- Stateless (cursor contains all pagination state)
"""

import base64
import json
from typing import List, Optional, Generic, TypeVar, Any
from pydantic import BaseModel, ConfigDict

T = TypeVar('T')


class PaginationCursor(BaseModel):
    """Cursor for pagination."""
    model_config = ConfigDict(from_attributes=True)

    last_id: int
    last_value: Optional[Any] = None  # For sorting by fields other than ID

    def encode(self) -> str:
        """Encode cursor to base64 string."""
        data = {
            "last_id": self.last_id,
            "last_value": self.last_value
        }
        json_str = json.dumps(data, default=str)
        return base64.urlsafe_b64encode(json_str.encode()).decode()

    @classmethod
    def decode(cls, cursor_str: str) -> "PaginationCursor":
        """Decode base64 cursor string."""
        try:
            json_str = base64.urlsafe_b64decode(cursor_str.encode()).decode()
            data = json.loads(json_str)
            return cls(**data)
        except Exception:
            raise ValueError("Invalid pagination cursor")


class PaginationMeta(BaseModel):
    """Metadata for paginated responses."""
    model_config = ConfigDict(from_attributes=True)

    cursor: Optional[str] = None  # Next page cursor
    has_more: bool = False  # Whether there are more items
    count: int  # Number of items in current page


class PaginationLinks(BaseModel):
    """Links for paginated responses."""
    model_config = ConfigDict(from_attributes=True)

    self: str
    next: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    model_config = ConfigDict(from_attributes=True)

    data: List[T]
    meta: PaginationMeta
    links: PaginationLinks


def create_pagination_cursor(
    items: List[Any],
    limit: int,
    sort_field: str = "id"
) -> Optional[str]:
    """
    Create pagination cursor from list of items.

    Args:
        items: List of items (should have 1 extra item to check has_more)
        limit: Requested page size
        sort_field: Field used for sorting (default: "id")

    Returns:
        Base64 encoded cursor string, or None if no more pages
    """
    if len(items) <= limit:
        # No more pages
        return None

    # Get last item from requested page (not the extra item)
    last_item = items[limit - 1]

    cursor = PaginationCursor(
        last_id=getattr(last_item, "id"),
        last_value=getattr(last_item, sort_field) if sort_field != "id" else None
    )

    return cursor.encode()


def paginate_query(
    query,
    cursor: Optional[str] = None,
    limit: int = 20,
    max_limit: int = 50,
    sort_field: str = "id",
    sort_desc: bool = False
):
    """
    Apply cursor-based pagination to SQLAlchemy query.

    Args:
        query: SQLAlchemy query object
        cursor: Pagination cursor string
        limit: Requested page size
        max_limit: Maximum allowed page size
        sort_field: Field to sort by (default: "id")
        sort_desc: Whether to sort descending

    Returns:
        Tuple of (paginated_query, actual_limit)
    """
    # Enforce max limit
    actual_limit = min(limit, max_limit)

    # Decode cursor if provided
    if cursor:
        try:
            cursor_obj = PaginationCursor.decode(cursor)

            # Apply cursor filter
            if sort_field == "id":
                if sort_desc:
                    query = query.filter(query.column_descriptions[0]['type'].id < cursor_obj.last_id)
                else:
                    query = query.filter(query.column_descriptions[0]['type'].id > cursor_obj.last_id)
            else:
                # For custom sort fields, need compound filter
                model = query.column_descriptions[0]['type']
                sort_column = getattr(model, sort_field)

                if sort_desc:
                    query = query.filter(
                        (sort_column < cursor_obj.last_value) |
                        ((sort_column == cursor_obj.last_value) & (model.id < cursor_obj.last_id))
                    )
                else:
                    query = query.filter(
                        (sort_column > cursor_obj.last_value) |
                        ((sort_column == cursor_obj.last_value) & (model.id > cursor_obj.last_id))
                    )
        except ValueError:
            # Invalid cursor, start from beginning
            pass

    # Request one extra item to check if there are more pages
    query = query.limit(actual_limit + 1)

    return query, actual_limit
