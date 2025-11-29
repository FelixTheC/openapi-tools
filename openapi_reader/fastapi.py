from pathlib import Path
from string import Template
from typing import Literal, Optional

from openapi_reader.schema import OpenAPIDefinition, Property
from openapi_reader.utils import Concurrency, write_data_to_file, INDENT, operation_id_to_function_name

BASE_IMPORT = [
    "from fastapi import APIRouter",
]
ASYNC_BASE_IMPORT = [
    "import requests",
]
SYNC_BASE_IMPORT = [
    "import aiohttp",
]

SERIALIZER_IMPORT = ["from pydantic import BaseModel"]


def string_constraints(type_info: dict) -> str:
    params = []

    if min_ := type_info.get("min_length"):
        params.append(f"min_length={min_}")
    if max_ := type_info.get("maxLength"):
        params.append(f"max_length={max_}")

    if params:
        return ",".join(params)
    return ""


def number_constraints(type_info: dict) -> str:
    params = []
    if min_ := type_info.get("minimum"):
        modifier = "gt" if type_info.get("exclusiveMinimum", True) else "ge"
        params.append(f"{modifier}={min_}")
    if max_ := type_info.get("maximum"):
        modifier = "lt" if type_info.get("exclusiveMaximum", True) else "le"
        params.append(f"{modifier}={max_}")
    if multiple_of := type_info.get("multipleOf"):
        params.append(f"multiple_of={multiple_of}")

    if params:
        return ",".join(params)
    return ""


def create_validator(field_name: str, field_type: str):
    function_name = f"optional_{operation_id_to_function_name(field_name)}"
    return Template(
        """
    @classmethod
    @field_validator("$field_name")
    def $function_name(cls, val: $field_type) -> $field_type:
        if val is not None:
            return val
        else:
            raise ValueError("$field_name may not be None")
        """
    ).substitute(field_name=field_name, function_name=function_name, field_type=field_type)


def serializer_func_from_property_type(prop) -> str:
    if not hasattr(prop.type, "__name__"):
        if prop.ref:
            return f"{prop.ref.name.title()}"
        raise ValueError
    match prop.type.__name__.lower():
        case "list":
            if isinstance(prop.ref, Property):
                return f"list[{prop.ref.type.__name__.lower()}]"
            return f"list[{prop.ref.properties[0].type.__name__.lower()}]"
        case "str" | "int" | "float" | "bool":
            return prop.type.__name__.lower()
        case "datetime" | "date":
            SERIALIZER_IMPORT[0] = "from datetime import datetime as dt"
            return f"dt.{prop.type.__name__.lower()}"
        case "enum" | "Enum":
            SERIALIZER_IMPORT[0] = "import enum"
            return prop.name.title()
        case _:
            if prop.ref:
                return f"{prop.ref.name.title()}"
            return "None"


ENUM_CLASS_TEMPLATE = Template("""
class $name(enum.Enum):
$values
""")


def create_enum_class(prop) -> str:
    attrs = []
    for enum_value in prop.enum_values:
        attrs.append(f"{enum_value.upper()} = '{enum_value}'")
    attrs_str = [f"{INDENT}{obj}\n" for obj in attrs]
    return ENUM_CLASS_TEMPLATE.substitute(name=prop.name.title(), values="".join(attrs_str))


def schema_to_fastapi(schema, enum_classes: dict, required_fields: tuple) -> str:
    properties: list[str] = []
    for prop in schema.properties:
        if prop.enum_values:
            if prop.name not in enum_classes:
                enum_classes[prop.name] = create_enum_class(prop)
        if prop.name not in required_fields:
            type_hint = f"Optional[{serializer_func_from_property_type(prop)}] = None"
        else:
            type_hint = serializer_func_from_property_type(prop)
        properties.append(f"{prop.name.lower()}: {type_hint}")
    return f"\n{INDENT}".join(properties)


def validators_from_schema(schema) -> str:
    return ""


def create_serializer_file(
    definition: OpenAPIDefinition,
    *,
    export_folder: Optional[Path] = None,
    use_tempdir: bool = False,
    concurrency: Concurrency = Concurrency.SYNC,
):
    schemas: list[str] = []
    enum_classes = {}
    for schema_name, schema in definition.created_schemas.items():
        schema_body = schema_to_fastapi(schema, enum_classes, tuple(schema.required_fields))
        validators = validators_from_schema(schema)
        schema_def = f"""
class {schema_name}(BaseModel):
    {schema_body}
    {validators}
    """
        if refs := schema.get_refs():
            min_idx = len(schemas)
            for ref in refs:
                if ref:
                    for idx, obj in enumerate(schemas):
                        if ref in obj:
                            min_idx = max(min_idx, idx)

            schemas.insert(min_idx + 1, schema_def)
        else:
            schemas.insert(0, schema_def)
    enum_schemas = list(enum_classes.values())
    schemas = enum_schemas + schemas
    from pprint import pprint

    pprint(schemas)
    # write_data_to_file(
    #     schemas,
    #     import_statements=INITIAL_FILE_INPUTS,
    #     file_name="serializers",
    #     export_folder=export_folder,
    #     use_tempdir=use_tempdir,
    # )
