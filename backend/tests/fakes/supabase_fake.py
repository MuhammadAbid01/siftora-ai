"""A small in-memory stand-in for the supabase-py client's table query
builder, realistic enough to exercise app/database.py's actual filter and
ownership logic without a live Supabase project.

Not a general-purpose fake: it implements only the operations
app/database.py actually calls (insert/select/update/delete with eq/lt/in_/
order/limit), plus the table-specific column defaults the real Postgres
schema (supabase/migrations/0002_campaigns.sql) applies on insert.
"""

import itertools
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

# A monotonically increasing offset guarantees distinct `created_at` values
# even when two inserts land within the same wall-clock tick (observed on
# Windows), which matters for cursor pagination tests that sort by it.
_insert_sequence = itertools.count()


def _next_timestamp() -> str:
    return (datetime.now(UTC) + timedelta(microseconds=next(_insert_sequence))).isoformat()


_CAMPAIGN_DEFAULTS: dict[str, Any] = {
    "offer": None,
    "target_lead_count": 20,
    "status": "draft",
    "search_plan": None,
    "score_weights": {
        "industry_fit": 20,
        "geography_fit": 10,
        "company_size_fit": 10,
        "pain_point_evidence": 20,
        "buying_signal": 15,
        "contact_relevance": 10,
        "recency": 10,
        "evidence_completeness": 5,
    },
    "score_threshold_qualified": 75,
    "score_threshold_needs_review": 55,
    "limit_max_queries": 20,
    "limit_max_pages_per_company": 5,
    "limit_max_retries": 2,
    "limit_max_cost_usd": 5.00,
    "plan_approved_at": None,
}

_CAMPAIGN_ICP_DEFAULTS: dict[str, Any] = {
    "industries": [],
    "locations": [],
    "company_size_min": None,
    "company_size_max": None,
    "signals": [],
    "exclusions": [],
    "target_roles": [],
}

_TABLE_DEFAULTS = {"campaigns": _CAMPAIGN_DEFAULTS, "campaign_icp": _CAMPAIGN_ICP_DEFAULTS}
_TABLE_KEY_COLUMN = {"campaigns": "id", "campaign_icp": "campaign_id"}

Op = Literal["select", "insert", "update", "delete"]


class FakeResult:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class FakeQuery:
    def __init__(
        self,
        table: dict[str, dict[str, Any]],
        table_name: str,
        op: Op,
        payload: dict[str, Any] | None = None,
    ):
        self._table = table
        self._table_name = table_name
        self._op = op
        self._payload = payload
        self._filters: list[tuple[str, str, Any]] = []
        self._order_col: str | None = None
        self._order_desc = False
        self._limit_n: int | None = None

    def eq(self, column: str, value: Any) -> "FakeQuery":
        self._filters.append(("eq", column, value))
        return self

    def lt(self, column: str, value: Any) -> "FakeQuery":
        self._filters.append(("lt", column, value))
        return self

    def in_(self, column: str, values: list[Any]) -> "FakeQuery":
        self._filters.append(("in", column, values))
        return self

    def order(self, column: str, desc: bool = False) -> "FakeQuery":
        self._order_col = column
        self._order_desc = desc
        return self

    def limit(self, n: int) -> "FakeQuery":
        self._limit_n = n
        return self

    def _matches(self, row: dict[str, Any]) -> bool:
        for kind, column, value in self._filters:
            if kind == "eq" and row.get(column) != value:
                return False
            if kind == "lt" and not (row.get(column) is not None and row[column] < value):
                return False
            if kind == "in" and row.get(column) not in value:
                return False
        return True

    def execute(self) -> FakeResult:
        if self._op == "insert":
            return self._execute_insert()
        if self._op == "select":
            return self._execute_select()
        if self._op == "update":
            return self._execute_update()
        if self._op == "delete":
            return self._execute_delete()
        raise NotImplementedError(self._op)

    def _execute_insert(self) -> FakeResult:
        assert self._payload is not None
        row = {**_TABLE_DEFAULTS.get(self._table_name, {}), **self._payload}
        now = _next_timestamp()
        row.setdefault("created_at", now)
        row.setdefault("updated_at", now)
        if self._table_name == "campaigns":
            row.setdefault("id", str(uuid.uuid4()))
        key_column = _TABLE_KEY_COLUMN[self._table_name]
        self._table[row[key_column]] = row
        return FakeResult([dict(row)])

    def _execute_select(self) -> FakeResult:
        rows = [dict(row) for row in self._table.values() if self._matches(row)]
        if self._order_col:
            rows.sort(key=lambda r: r[self._order_col], reverse=self._order_desc)
        if self._limit_n is not None:
            rows = rows[: self._limit_n]
        return FakeResult(rows)

    def _execute_update(self) -> FakeResult:
        assert self._payload is not None
        updated = []
        for row in self._table.values():
            if self._matches(row):
                row.update(self._payload)
                row["updated_at"] = datetime.now(UTC).isoformat()
                updated.append(dict(row))
        return FakeResult(updated)

    def _execute_delete(self) -> FakeResult:
        keys_to_delete = [key for key, row in self._table.items() if self._matches(row)]
        deleted = [dict(self._table[key]) for key in keys_to_delete]
        for key in keys_to_delete:
            del self._table[key]
        return FakeResult(deleted)


class FakeTable:
    def __init__(self, table: dict[str, dict[str, Any]], name: str) -> None:
        self._table = table
        self._name = name

    def insert(self, payload: dict[str, Any]) -> FakeQuery:
        return FakeQuery(self._table, self._name, "insert", payload)

    def select(self, *_columns: str) -> FakeQuery:
        return FakeQuery(self._table, self._name, "select")

    def update(self, payload: dict[str, Any]) -> FakeQuery:
        return FakeQuery(self._table, self._name, "update", payload)

    def delete(self) -> FakeQuery:
        return FakeQuery(self._table, self._name, "delete")


class FakeSupabaseClient:
    """Stand-in for `supabase.Client`, scoped to what app/database.py uses."""

    def __init__(self) -> None:
        self._tables: dict[str, dict[str, dict[str, Any]]] = {}

    def table(self, name: str) -> FakeTable:
        return FakeTable(self._tables.setdefault(name, {}), name)
