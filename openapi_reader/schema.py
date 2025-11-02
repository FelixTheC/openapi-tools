import enum
import datetime as dt
import typing
from dataclasses import dataclass
from typing import Literal, Optional

from openapi_reader.utils import HTTPResponse, convert_camel_case_to_snake_case


class SchemaType(enum.Enum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass(slots=True)
class Property:
    name: str
    example: None | str | int | float | bool | list
    type: object
    enum_values: list  # can be empty
    ref: Optional["Schema"] | Optional["Property"] = None


@dataclass(slots=True)
class Schema:
    name: str
    properties: list[Property]
    typ: SchemaType

    def get_refs(self) -> list[str]:
        refs = []
        for prop in self.properties:
            if prop.ref:
                refs.append(prop.ref.name)
        return refs

    def get_type_hint_str(self) -> str:
        match self.typ:
            case SchemaType.STRING:
                return "str"
            case SchemaType.INTEGER:
                return "int"
            case SchemaType.NUMBER:
                return "float"
            case SchemaType.BOOLEAN:
                return "bool"
            case SchemaType.ARRAY:
                if str(self.properties[0].type).lower() == "enum":
                    return "list[str]"
                if "list" in str(self.properties[0].type):
                    if self.properties[0].ref:
                        if isinstance(self.properties[0].ref, Property):
                            return f"list[{self.properties[0].ref.type.__name__}]"
                        else:
                            return f"list[{self.properties[0].ref.get_type_hint_str()}]"
                    else:
                        return "list"
                return f"list[{str(self.properties[0].type)}]"
            case SchemaType.OBJECT:
                return "dict"


@dataclass(slots=True)
class ResponseSchema:
    required: bool
    type: SchemaType
    schema: Schema


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
    response_schema: dict[str, ResponseSchema]
    tags: list[str]
    parameters: list[QueryParam]
    request_schema_required: bool = False

    def get_success_response_schema(self) -> Optional[ResponseSchema]:
        for status_code, schema in self.response_schema.items():
            if HTTPResponse.OK.value <= int(status_code) <= HTTPResponse.IM_USED.value:
                return schema
        return None

    def get_success_error_code(self) -> HTTPResponse:
        for status_code, schema in self.response_schema.items():
            if HTTPResponse.OK.value <= int(status_code) <= HTTPResponse.IM_USED.value:
                return HTTPResponse(int(status_code))
        return HTTPResponse.OK

    def get_fail_error_code(self) -> HTTPResponse:
        for status_code, schema in self.response_schema.items():
            if HTTPResponse.BAD_REQUEST.value <= int(status_code) <= HTTPResponse.INTERNAL_SERVER_ERROR.value:
                return HTTPResponse(int(status_code))
        return HTTPResponse.BAD_REQUEST


@dataclass(slots=True)
class ApiPath:
    path: str
    methods: list[Method]

    def get_query_params(self) -> list[str]:
        res = []
        for method in self.methods:
            res.extend(
                [
                    f"{convert_camel_case_to_snake_case(param.name)}: {param.schema.get_type_hint_str()}"
                    for param in method.parameters
                    if param.position == "query"
                ]
            )
        return res


class OpenAPIDefinition:
    paths: list[ApiPath]
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
        for key, value in required_schemas.items():
            self.created_schemas[key] = Schema(
                name=key, properties=create_properties(value, required_schemas), typ=SchemaType(value["type"])
            )

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
                        # TODO fix me
                        typ=SchemaType(request_schema_def.get("type", "object")),
                    )
                else:
                    request_schema = self.created_schemas[request_schema_name]
                responses = data.get("responses", {})
                response_schemas = {}
                for status_code, response in responses.items():
                    if "content" in response:
                        resp_content = response["content"].get("application/json", {}).get("schema", {})
                        if "$ref" in resp_content:
                            schema = self.created_schemas[resp_content.get("$ref", "").split("/")[-1]]
                            response_schema = ResponseSchema(
                                required=True,
                                type=SchemaType("object"),
                                schema=schema,
                            )
                        else:
                            resp_schema_typ = resp_content.get("type", "")
                            try:
                                schema = self.created_schemas[resp_content.get("items").get("$ref", "").split("/")[-1]]
                            except AttributeError:
                                props = []
                                for key, val in resp_content.items():
                                    if key == "type":
                                        continue
                                    props.append(
                                        Property(
                                            name="", example=val.get("default"), type=val.get("type"), enum_values=[]
                                        )
                                    )
                                response_schema = ResponseSchema(
                                    required=True,
                                    type=SchemaType(resp_schema_typ),
                                    schema=Schema(name=request_schema_name, properties=props, typ=SchemaType("object")),
                                )
                            else:
                                response_schema = ResponseSchema(
                                    required=True,
                                    type=SchemaType(resp_schema_typ),
                                    schema=schema,
                                )
                    else:
                        response_schema = None
                    if status_code == "default":
                        status_code = HTTPResponse.OK.value
                    response_schemas[status_code] = response_schema
                method_data.append(
                    Method(
                        operation_id=data["operationId"],
                        request_type=method,
                        request_schema=request_schema,
                        response_schema=response_schemas,
                        tags=data.get("tags", []),
                        parameters=create_parameters(data.get("parameters", []), self.created_schemas),
                    )
                )
            self.paths.append(
                ApiPath(
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


def create_item_schema(item: dict, existing_schemas: dict = {}) -> None | Schema | Property:
    """
    :param item: the part after the schema name
    :param existing_schemas: all schemas from the openapi file
    :return: A new Property object
    """
    key, val = list(item.items())[0]
    if key == "$ref":
        schema_name = val.split("/")[-1]
        existing_schema: dict = existing_schemas[schema_name]

        try:
            return Schema(
                name=schema_name,
                properties=create_properties(existing_schema, existing_schemas),
                typ=existing_schema["type"],
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
            prop.ref = create_item_schema(items, existing_schemas)
        if "$ref" in value:
            prop.ref = create_item_schema(value, existing_schemas)

        properties.append(prop)
    return properties


def create_parameters(data: list, existing_schemas: dict = {}) -> list[QueryParam]:
    res: list[QueryParam] = []

    for obj in data:
        properties = []

        prop = Property(
            name="",
            example=obj["schema"].get("example"),
            type=convert_type(obj["schema"].get("type", ""), obj["schema"].get("format")),
            enum_values=obj["schema"].get("enum", []),
        )
        if prop.enum_values:
            prop.type = enum.Enum
        if prop.type == list:
            items = obj["schema"].get("items")
            prop.ref = create_item_schema(items, existing_schemas)

        properties.append(prop)
        res.append(
            QueryParam(
                description=obj.get("description", ""),
                explode=obj.get("explode", False),
                position=obj.get("in", "query"),
                name=obj.get("name", ""),
                required=obj.get("required", False),
                schema=Schema(name="", properties=properties, typ=SchemaType(obj["schema"].get("type", "object"))),
            ),
        )

    return res
