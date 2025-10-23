import enum
import datetime as dt
from dataclasses import dataclass
from typing import Literal, Optional


@dataclass(slots=True)
class Property:
    name: str
    example: None | str | int | float | bool | list
    type: object
    enum_values: list  # can be empty
    ref: Optional["Schema"] = None


@dataclass(slots=True)
class Schema:
    name: str
    properties: list[Property]


@dataclass(slots=True)
class QueryParam:
    description: str
    explode: bool
    position: str
    name: str
    required: bool
    schema: Schema


@dataclass(slots=True)
class Method:
    operation_id: str
    request_type: Literal["get", "post", "put", "delete"]
    request_schema: Schema
    response_schema: dict[str, Schema]
    tags: list[str]
    request_schema_required: bool = False


@dataclass(slots=True)
class Path:
    path: str
    methods: list[Method]


class OpenAPIDefinition:
    paths: list[Path]
    # to check if a schema already exists which we can reuse directly
    created_schemas: dict[str, Schema]
    __openapi_data: dict

    __slots__ = ("paths", "created_schemas", "__openapi_data")

    def __init__(self, yaml_data: dict):
        self.__openapi_data = yaml_data
        self.created_schemas = {}
        self.paths = []

    def _extract_schemas(self):
        required_schemas = self.__openapi_data["components"]["schemas"]
        """
        Order {'type': 'object', 'properties': {'id': {'type': 'integer', 'format': 'int64', 'example': 10}, 'petId': {'type': 'integer', 'format': 'int64', 'example': 198772}, 'quantity': {'type': 'integer', 'format': 'int32', 'example': 7}, 'shipDate': {'type': 'string', 'format': 'date-time'}, 'status': {'type': 'string', 'description': 'Order Status', 'example': 'approved', 'enum': ['placed', 'approved', 'delivered']}, 'complete': {'type': 'boolean'}}, 'xml': {'name': 'order'}}
        """
        for key, value in required_schemas.items():
            self.created_schemas[key] = Schema(name=key, properties=create_properties(value, required_schemas))

    def _extract_paths(self):
        required_paths = self.__openapi_data["paths"]
        for path, methods in required_paths.items():
            method_data = []
            for method, data in methods.items():
                request_schema_name = (
                    data.get("requestBody", {})
                    .get("content", {})
                    .get("application/json", {})
                    .get("schema", {})
                    .get("$ref", "")
                    .split("/")[-1]
                )
                if not request_schema_name:
                    request_schema_def = (
                        data.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {})
                    )
                    request_schema = Schema(
                        name="",
                        properties=[
                            Property(
                                name="",
                                example=request_schema_def.get("default", ""),
                                type=request_schema_def.get("type", ""),
                                enum_values=request_schema_def.get("enum", []),
                            )
                        ],
                    )
                else:
                    request_schema = self.created_schemas[request_schema_name]
                responses = data.get("responses", {})
                response_schemas = {}
                for status_code, response in responses.items():
                    if "content" in response:
                        response_schema = (
                            response["content"]
                            .get("application/json", {})
                            .get("schema", {})
                            .get("$ref", "")
                            .split("/")[-1]
                        )
                    else:
                        response_schema = None
                    response_schemas[status_code] = response_schema
                method_data.append(
                    Method(
                        operation_id=data["operationId"],
                        request_type=method,
                        request_schema=request_schema,
                        response_schema=response_schemas,
                        tags=data.get("tags", []),
                    )
                )
            self.paths.append(
                Path(
                    path=path,
                    methods=method_data,
                )
            )


def convert_type(typ: str, value_format: str | None = None):
    match typ:
        case "string":
            if value_format:
                match value_format:
                    case "date-time":
                        return dt.datetime
                    case "date":
                        return dt.date
            return str
        case "integer":
            return int
        case "number":
            return float
        case "boolean":
            return bool
        case "array":
            return list
        case _:
            return None


def create_itemschema(item: dict, existing_schemas: dict = {}) -> Property | Schema:
    """
    :param item: the part after the schema name
    :param existing_schemas: all schemas from the openapi file
    :return: A new Property object
    """
    key, val = list(item.items())[0]
    if key == "$ref":
        schema_name = val.split("/")[-1]
        try:
            return Schema(
                name=schema_name, properties=create_properties(existing_schemas[schema_name], existing_schemas)
            )
        except KeyError:
            # should never happen
            # TODO find a better solution
            pass
        except IndexError:
            # should never happen
            # TODO find a better solution
            pass
    else:
        if isinstance(val, dict):
            return Property(name="", example="", type=convert_type(val.get("type")), enum_values=[])
        return Property(name="", example="", type=convert_type(val), enum_values=[])


def create_properties(data: dict, existing_schemas: dict = {}) -> list[Property]:
    properties = []
    for key, value in data["properties"].items():
        prop = Property(
            name=key,
            example=value.get("example"),
            type=convert_type(value.get("type", ""), value.get("format")),
            enum_values=value.get("enum", []),
        )
        if prop.enum_values:
            prop.type = enum.Enum
        if prop.type == list:
            items = value.get("items")
            prop.ref = create_itemschema(items, existing_schemas)
        if "$ref" in value:
            prop.ref = create_itemschema(value, existing_schemas)

        properties.append(prop)
    return properties
