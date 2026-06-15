"""
Query Builder module to safely convert JSON filters from AI into SQL queries.
"""

from typing import List, Any, Dict, Tuple
from pydantic import BaseModel, Field

# Valid fields to prevent SQL injection or arbitrary queries
ALLOWED_FIELDS = {
    "city": "city",
    "gender": "gender",
    "tags": "tags",
    "total_spent": "total_spent",
    "total_orders": "total_orders",
    "days_since_last_order": "(julianday('now') - julianday(last_order_date))",
    "health_score": "health_score",
    "status": "status"
}

ALLOWED_OPERATORS = {
    "eq": "=",
    "neq": "!=",
    "gt": ">",
    "lt": "<",
    "gte": ">=",
    "lte": "<=",
    "contains": "LIKE"
}


class FilterCondition(BaseModel):
    field: str
    operator: str
    value: Any

class JSONFilter(BaseModel):
    conditions: List[FilterCondition]
    logic: str = "AND"


def build_sql_from_filter(json_filter: dict) -> Tuple[str, list]:
    """
    Safely converts a JSON filter dictionary into a parameterized SQL WHERE clause.
    Returns (sql_string, parameters_list).
    """
    try:
        filter_data = JSONFilter(**json_filter)
    except Exception as e:
        raise ValueError(f"Invalid filter format: {e}")

    if not filter_data.conditions:
        return "SELECT * FROM customers", []

    logic_op = " AND " if filter_data.logic.upper() == "AND" else " OR "
    clauses = []
    params = []

    for cond in filter_data.conditions:
        if cond.field not in ALLOWED_FIELDS:
            continue  # Ignore invalid fields safely
        if cond.operator not in ALLOWED_OPERATORS:
            continue  # Ignore invalid operators safely

        db_field = ALLOWED_FIELDS[cond.field]
        db_op = ALLOWED_OPERATORS[cond.operator]

        if cond.operator == "contains":
            clauses.append(f"{db_field} {db_op} ?")
            params.append(f"%{cond.value}%")
        else:
            clauses.append(f"{db_field} {db_op} ?")
            params.append(cond.value)

    if not clauses:
        return "SELECT * FROM customers", []

    where_clause = logic_op.join(clauses)
    query = f"SELECT * FROM customers WHERE {where_clause}"
    
    return query, params
