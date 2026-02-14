"""WHERE clause parser for converting SQL-like strings to BSL filters.

Converts SQL WHERE clauses to BSL filter dictionaries:
- "region = 'US'" → {"region": "US"}
- "date >= '2024-01-01'" → {"date": {"gte": "2024-01-01"}}
- "region = 'US' AND date >= '2024-01-01'" → {"region": "US", "date": {"gte": "2024-01-01"}}
"""
from __future__ import annotations

import re
from typing import Any


def parse_where_clause(where: str) -> dict[str, Any] | None:
    """Parse SQL WHERE clause string into BSL filter dict.
    
    Supported operators:
    - = (equality)
    - >, >=, <, <= (comparisons)
    - IN (list membership)
    - AND (multiple conditions)
    
    Examples:
        >>> parse_where_clause("region = 'US'")
        {"region": "US"}
        
        >>> parse_where_clause("date >= '2024-01-01' AND date <= '2024-12-31'")
        {"date": {"gte": "2024-01-01", "lte": "2024-12-31"}}
        
        >>> parse_where_clause("region IN ('US', 'EU')")
        {"region": ["US", "EU"]}
    
    Args:
        where: SQL WHERE clause string (without the WHERE keyword)
        
    Returns:
        BSL filter dict, or None if parsing fails
    """
    if not where or not where.strip():
        return None
    
    filters: dict[str, Any] = {}
    
    # Split by AND (simple approach - doesn't handle OR yet)
    conditions = re.split(r'\s+AND\s+', where.strip(), flags=re.IGNORECASE)
    
    for condition in conditions:
        condition = condition.strip()
        if not condition:
            continue
        
        # Try to parse the condition
        parsed = _parse_condition(condition)
        if parsed:
            dimension, value = parsed
            
            # Merge filters for the same dimension
            if dimension in filters:
                # If it's a dict (like {"gte": "2024-01-01"}), merge it
                if isinstance(filters[dimension], dict) and isinstance(value, dict):
                    filters[dimension] = {**filters[dimension], **value}
                else:
                    # Otherwise, overwrite (last one wins)
                    filters[dimension] = value
            else:
                filters[dimension] = value
    
    return filters if filters else None


def _parse_condition(condition: str) -> tuple[str, Any] | None:
    """Parse a single condition into (dimension, value).
    
    Returns:
        Tuple of (dimension_name, filter_value) or None if parse fails
    """
    # Pattern: dimension OPERATOR value
    # Try IN operator first (has parentheses)
    in_match = re.match(
        r"^(\w+)\s+IN\s*\(\s*(.+?)\s*\)$",
        condition,
        re.IGNORECASE
    )
    if in_match:
        dimension = in_match.group(1).strip()
        values_str = in_match.group(2).strip()
        # Parse comma-separated values
        values = []
        for val in values_str.split(','):
            val = val.strip()
            parsed_val = _parse_value(val)
            if parsed_val is not None:
                values.append(parsed_val)
        return (dimension, values) if values else None
    
    # Try comparison operators (>=, <=, !=, =, >, <)
    # Order matters: check >= before >, <= before <
    for op_pattern, bsl_op in [
        (r">=", "gte"),
        (r"<=", "lte"),
        (r"!=", "ne"),
        (r">", "gt"),
        (r"<", "lt"),
        (r"=", None),  # None means direct equality
    ]:
        pattern = rf"^(\w+)\s*{re.escape(op_pattern)}\s*(.+)$"
        match = re.match(pattern, condition)
        if match:
            dimension = match.group(1).strip()
            value_str = match.group(2).strip()
            value = _parse_value(value_str)
            
            if value is None:
                return None
            
            # For equality, return value directly
            if bsl_op is None:
                return (dimension, value)
            
            # For comparisons, return {"gte": value} etc.
            return (dimension, {bsl_op: value})
    
    return None


def _parse_value(value_str: str) -> Any | None:
    """Parse a value string into appropriate Python type.
    
    Handles:
    - Quoted strings: 'US' or "US" → "US"
    - Numbers: 100 → 100, 3.14 → 3.14
    - Booleans: true/false → True/False
    - Dates: Auto-detected as strings
    
    Returns:
        Parsed value or None if invalid
    """
    value_str = value_str.strip()
    
    # Quoted string
    if (value_str.startswith("'") and value_str.endswith("'")) or \
       (value_str.startswith('"') and value_str.endswith('"')):
        return value_str[1:-1]
    
    # Boolean
    if value_str.lower() == "true":
        return True
    if value_str.lower() == "false":
        return False
    
    # Number (int or float)
    try:
        if '.' in value_str:
            return float(value_str)
        return int(value_str)
    except ValueError:
        pass
    
    # Unquoted string (treat as string literal)
    return value_str


# Convenience function for testing
def _test_parser() -> None:
    """Test the WHERE clause parser."""
    test_cases = [
        ("region = 'US'", {"region": "US"}),
        ("date >= '2024-01-01'", {"date": {"gte": "2024-01-01"}}),
        ("date >= '2024-01-01' AND date <= '2024-12-31'", 
         {"date": {"gte": "2024-01-01", "lte": "2024-12-31"}}),
        ("region IN ('US', 'EU', 'APAC')", {"region": ["US", "EU", "APAC"]}),
        ("revenue > 1000", {"revenue": {"gt": 1000}}),
        ("active = true", {"active": True}),
        ("region = 'US' AND revenue >= 100", {"region": "US", "revenue": {"gte": 100}}),
    ]
    
    print("Testing WHERE clause parser:")
    for where, expected in test_cases:
        result = parse_where_clause(where)
        status = "PASS" if result == expected else "FAIL"
        print(f"{status}: {where}")
        if result != expected:
            print(f"  Expected: {expected}")
            print(f"  Got: {result}")


if __name__ == "__main__":
    _test_parser()
