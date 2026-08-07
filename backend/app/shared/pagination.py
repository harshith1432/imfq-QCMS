from math import ceil

def paginate_query(query, page=1, per_page=25, serializer_fn=None):
    """
    Standardized Enterprise Pagination Utility.
    Executes pagination at SQL level and returns standard JSON payload format:
    {
        "items": [...],
        "page": 1,
        "per_page": 25,
        "total": 15420,
        "total_pages": 617,
        "has_next": true,
        "has_prev": false
    }
    """
    try:
        per_page = int(per_page)
    except (ValueError, TypeError):
        per_page = 25
    per_page = max(1, min(per_page, 250))

    try:
        page = int(page)
    except (ValueError, TypeError):
        page = 1
    page = max(1, page)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    if serializer_fn:
        items = [serializer_fn(item) for item in pagination.items]
    else:
        items = pagination.items

    return {
        "items": items,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "total_pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev
    }

def apply_sorting(query, model, sort_by, order='asc', allowed_columns=None):
    """
    Helper to safely apply SQL-level column sorting.
    """
    if not sort_by:
        return query
        
    sort_by = str(sort_by).strip()
    order = str(order).lower().strip()
    
    if allowed_columns and sort_by not in allowed_columns:
        return query
        
    if hasattr(model, sort_by):
        col_attr = getattr(model, sort_by)
        if order == 'desc':
            query = query.order_by(col_attr.desc())
        else:
            query = query.order_by(col_attr.asc())
            
    return query
