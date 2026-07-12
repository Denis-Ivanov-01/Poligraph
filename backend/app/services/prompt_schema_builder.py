from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.inspection import inspect


EnumValues = Mapping[str, Any] | Iterable[str]
FieldSpec = str | tuple[str, str]


def enum_contract(values: EnumValues) -> str:
    if isinstance(values, Mapping):
        ordered = values.keys()
    else:
        ordered = sorted(values)
    return " | ".join(str(value) for value in ordered)


def enum_list_contract(values: EnumValues) -> list[str]:
    return [f"one or more of: {enum_contract(values)}"]


def _column_type_contract(column_type: Any, *, nullable: bool) -> Any:
    if isinstance(column_type, Boolean):
        return "boolean or null" if nullable else "boolean"
    if isinstance(column_type, Integer):
        return "integer or null" if nullable else 1
    if isinstance(column_type, DateTime):
        return "ISO-8601 datetime or null" if nullable else "ISO-8601 datetime"
    if isinstance(column_type, Date):
        return "YYYY-MM-DD or null" if nullable else "YYYY-MM-DD"
    if isinstance(column_type, JSONB):
        return "array/object or null" if nullable else "array/object"
    if isinstance(column_type, (String, Text)):
        return "string or null" if nullable else "string"
    return "value or null" if nullable else "value"


def db_field_contract(
    model: type[Any],
    field_name: str,
    *,
    enum_values: EnumValues | None = None,
    nullable: bool | None = None,
    example: Any = None,
) -> Any:
    column = inspect(model).columns[field_name]
    effective_nullable = column.nullable if nullable is None else nullable
    if enum_values is not None:
        value = enum_contract(enum_values)
        return f"{value} or null" if effective_nullable else value
    if example is not None:
        return example
    return _column_type_contract(column.type, nullable=effective_nullable)


def db_fields_contract(
    model: type[Any],
    fields: Sequence[FieldSpec],
    *,
    enum_fields: Mapping[str, EnumValues] | None = None,
    nullable_overrides: Mapping[str, bool] | None = None,
    examples: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    enum_fields = enum_fields or {}
    nullable_overrides = nullable_overrides or {}
    examples = examples or {}
    result: dict[str, Any] = {}
    for field in fields:
        output_name, column_name = field if isinstance(field, tuple) else (field, field)
        result[output_name] = db_field_contract(
            model,
            column_name,
            enum_values=enum_fields.get(output_name) or enum_fields.get(column_name),
            nullable=nullable_overrides.get(output_name, nullable_overrides.get(column_name)),
            example=examples.get(output_name, examples.get(column_name)),
        )
    return result
