from pathlib import Path
import datetime as dt
import enum

from openapi_reader.reader import read_openapi_schema
from openapi_reader.schema import OpenAPIDefinition, Property, create_properties, create_parameters


def test_openapi_definition():
    definition = OpenAPIDefinition(read_openapi_schema(Path(__file__).parent / "openapi.yaml"))
    assert definition


def test_openapi_definition_create_schemas(openapi_yaml):
    definition = OpenAPIDefinition(openapi_yaml)
    definition._extract_schemas()
    assert len(definition.created_schemas) == 8
    required_schemas = ["Address", "ApiResponse", "Category", "Customer", "Order", "Pet", "Tag", "User"]
    assert all(schema in definition.created_schemas for schema in required_schemas)


def test_create_parameters():
    parameters = [
        {
            "description": "Status values that need to be considered for filter",
            "explode": True,
            "in": "query",
            "name": "status",
            "required": False,
            "schema": {"default": "available", "enum": ["available", "pending", "sold"], "type": "string"},
        }
    ]
    res = create_parameters(parameters, {})
    assert len(res) == 1
    assert len(res[0].schema.properties) == 1
    assert res[0].schema.properties[0].enum_values == ["available", "pending", "sold"]


def test_openapi_definition_creates_paths(openapi_yaml):
    definition = OpenAPIDefinition(openapi_yaml)
    definition._extract_schemas()
    definition._extract_paths()
    from pprint import pprint

    pprint(definition.paths)
    assert len(definition.paths) == 13
    # required_schemas = ["Address", "ApiResponse", "Category", "Customer", "Order", "Pet", "Tag", "User"]
    # assert all(schema in definition.created_schemas for schema in required_schemas)


def test_create_properties():
    data = {
        "type": "object",
        "properties": {
            "id": {"type": "integer", "format": "int64", "example": 10},
            "petId": {"type": "integer", "format": "int64", "example": 198772},
            "quantity": {"type": "integer", "format": "int32", "example": 7},
            "shipDate": {"type": "string", "format": "date-time"},
            "status": {
                "type": "string",
                "description": "Order Status",
                "example": "approved",
                "enum": ["placed", "approved", "delivered"],
            },
            "complete": {"type": "boolean"},
        },
        "xml": {"name": "order"},
    }
    results = [
        Property(name="id", example=10, type=int, enum_values=[]),
        Property(name="petId", example=198772, type=int, enum_values=[]),
        Property(name="quantity", example=7, type=int, enum_values=[]),
        Property(name="shipDate", example=None, type=dt.datetime, enum_values=[]),
        Property(name="status", example="approved", type=enum.Enum, enum_values=["placed", "approved", "delivered"]),
        Property(name="complete", example=None, type=bool, enum_values=[]),
    ]
    props = create_properties(data)
    assert all(prop in results for prop in props)


def test_create_drf_serializers(openapi_yaml):
    definition = OpenAPIDefinition(openapi_yaml)
    definition._extract_schemas()
    definition._extract_paths()

    from openapi_reader.drf import create_serializer_file

    create_serializer_file(definition)


def test_create_view_funcs(openapi_yaml):
    definition = OpenAPIDefinition(openapi_yaml)
    definition._extract_schemas()
    definition._extract_paths()

    from openapi_reader.drf import create_view_file

    create_view_file(definition)
