from pathlib import Path
import datetime as dt
import enum

import pytest

from openapi_reader.reader import read_openapi_schema
from openapi_reader.schema import OpenAPIDefinition, Property, create_properties, create_parameters, SchemaType


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
    definition.parse()

    assert len(definition.paths) == 13
    required_schemas = ["Address", "ApiResponse", "Category", "Customer", "Order", "Pet", "Tag", "User"]
    assert all(schema in definition.created_schemas for schema in required_schemas)


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
        Property(name="id", example=10, type_=int, enum_values=[]),
        Property(name="petId", example=198772, type_=int, enum_values=[]),
        Property(name="quantity", example=7, type_=int, enum_values=[]),
        Property(name="shipDate", example=None, type_=dt.datetime, enum_values=[]),
        Property(name="status", example="approved", type_=enum.Enum, enum_values=["placed", "approved", "delivered"]),
        Property(name="complete", example=None, type_=bool, enum_values=[]),
    ]
    props = create_properties(data, OpenAPIDefinition({}))
    assert all(prop in results for prop in props)


def test_extract_components_parameters(openapi_example_yaml):
    definition = OpenAPIDefinition(openapi_example_yaml)
    definition._extract_parameter_schemas()
    assert len(definition.parameter_schemas) == 2
    assert definition.parameter_schemas["limit"]
    assert definition.parameter_schemas["limit"].schema.properties[0].additional_requirements["minimum"] == 1
    assert definition.parameter_schemas["limit"].schema.properties[0].additional_requirements["maximum"] == 100
    assert definition.parameter_schemas["offset"]
    assert definition.parameter_schemas["offset"].schema.properties[0].additional_requirements["minimum"] == 0
    with pytest.raises(KeyError):
        assert definition.parameter_schemas["offset"].schema.properties[0].additional_requirements["maximum"] == 100


def test_extract_reference_schema(openapi_example_yaml):
    definition = OpenAPIDefinition(openapi_example_yaml)
    schema = OpenAPIDefinition.extract_reference(definition, "#/components/schemas/Error")
    assert schema.name == "Error"
    assert schema.typ == SchemaType.OBJECT
    assert len(schema.properties) == 3
    assert len(schema.required_fields) == 2
    assert definition.created_schemas["Error"] == schema


def test_extract_invalid_reference_schema(subtests: pytest.Subtests, openapi_example_yaml):
    definition = OpenAPIDefinition(openapi_example_yaml)
    for invalid_ref in ("", "#/components/schemas/NotExisting", "components/Error/schemas", "lorem/ipsum"):
        with subtests.test(invalid_ref=invalid_ref):
            schema = OpenAPIDefinition.extract_reference(definition, invalid_ref)
            assert schema is None
