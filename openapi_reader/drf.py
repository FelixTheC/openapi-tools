# function which creates serializer class with validators from a list `Schema` objects
# function which creates the request and response objects from a list of `Method` objects
from pathlib import Path
from unittest import case

from openapi_reader.schema import OpenAPIDefinition, Schema, Property

SERIALIZERS = {
    "str": "serializers.CharField()",  # can be extended
    "email": "serializers.EmailField()",
    "datetime": "serializer.DateTimeField()",
    "int": "serializers.IntegerField()",
    "float": "serializers.FloatField()",
    "enum": "serializers.CharField()",
    "bool": "serializers.BooleanField()",
}

INITIAL_FILE_INPUTS = ["from rest_framework import serializers"]


def serializer_func_from_property_type(prop: Property) -> str:
    if not hasattr(prop.type, "__name__"):
        if prop.ref:
            return f"{prop.ref.name.title()}Serializer()"
        raise ValueError
    match prop.type.__name__.lower():
        case "list":
            if prop.ref.name:
                return f"{prop.ref.name.title()}Serializer(many=True)"
            if isinstance(prop.ref, Property):
                return SERIALIZERS[prop.ref.type.__name__.lower()]
            return SERIALIZERS[prop.ref.properties[0].type.__name__.lower()]
        case "str":
            if prop.example and ("@" in prop.example or "email" in prop.name):
                return SERIALIZERS["email"]
            return SERIALIZERS["str"]
        case "datetime" | "date":
            return SERIALIZERS["datetime"]
        case "int":
            return SERIALIZERS["int"]
        case "float":
            return SERIALIZERS["float"]
        case "enum" | "Enum":
            return SERIALIZERS["enum"]
        case "bool":
            return SERIALIZERS["bool"]
        case _:
            if prop.ref:
                return f"{prop.ref.name.title()}Serializer()"
            return "None"


def schema_to_drf(schema: Schema) -> str:
    """
    Converts the openapi schema to the body of a Serializer class from django-rest-framework
    :param schema: a Schema object from the openapi definition
    :return: the string body for django-rest-framework serializer class
    """
    properties: list[str] = []
    for prop in schema.properties:
        properties.append(f"{prop.name.lower()} = {serializer_func_from_property_type(prop)}")
    return "\n\t".join(properties)


# maybe return path to file instead of `None`
def create_serializer_file(definition: OpenAPIDefinition) -> None:
    schemas: list[str] = []
    for schema_name, schema in definition.created_schemas.items():
        schema_body = schema_to_drf(schema)
        schema_def = f"""
class {schema_name}Serializer(serializers.Serializer):
    {schema_body}
"""
        schemas.append(schema_def)

    with (Path(__file__).parent / "example.py").open("w") as fp:
        for head in INITIAL_FILE_INPUTS:
            fp.write(head)
            fp.write("\n")

        for obj in schemas:
            fp.write(obj)
