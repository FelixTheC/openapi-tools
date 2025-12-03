import enum
import datetime as dt
import typing
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal, Optional

from openapi_reader.utils import HTTPResponse, convert_camel_case_to_snake_case, to_class_name


class SchemaType(enum.Enum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


DEFAULT_PROPERTIES = ("readOnly", "nullable", "default", "writeOnly", "deprecated")

ADDITIONAL_PROPERTIES = {
    "string": ("minLength", "maxLength", "pattern", "format") + DEFAULT_PROPERTIES,
    "integer": ("minimum", "maximum", "format") + DEFAULT_PROPERTIES,
    "number": ("minimum", "maximum", "format", "multipleOf") + DEFAULT_PROPERTIES,
    "array": ("minItems", "maxItems", "uniqueItems") + DEFAULT_PROPERTIES,
    "object": ("minProperties", "maxProperties") + DEFAULT_PROPERTIES,
}


@dataclass(slots=True)
class Property:
    name: str
    example: None | str | int | float | bool | list
    type: object | list[object]
    enum_values: list  # can be empty
    ref: Optional["Schema"] | Optional["Property"]
    additional_requirements: dict

    def __init__(self, name, example, type_, enum_values, ref=None, additional_requirements=None):
        self.name = name
        self.example = example
        self.type = type_
        self.enum_values = enum_values
        self.ref = ref
        self.additional_requirements = additional_requirements or {}


class CombinedSchema(typing.TypedDict):
    kind: Literal["oneOf", "anyOf", "allOf"]
    schemas: tuple["Schema", ...]


@dataclass(slots=True)
class Schema:
    name: str
    properties: list[Property]
    typ: SchemaType
    required_fields: set[str]
    nullable_fields: set[str]
    read_only_fields: set[str]
    combined_schemas: Optional[CombinedSchema] = None

    def __init__(
        self,
        name,
        properties,
        typ,
        required_fields,
        nullable_fields: Optional[set] = None,
        read_only_fields: Optional[set] = None,
    ):
        self.name = name
        self.properties = properties
        self.typ = typ
        self.required_fields = required_fields
        self.nullable_fields = nullable_fields or set()
        self.read_only_fields = read_only_fields or set()
        self.combined_schemas = None

    def get_refs(self) -> list[str]:
        refs = []
        for prop in self.properties:
            if prop.ref:
                refs.append(prop.ref.name)
        return refs

    def get_type_hint_str(self) -> str:
        match self.typ:
            case SchemaType.STRING:
                if self.properties[0].enum_values:
                    return f"typing.Literal[{', '.join(map(lambda x: f'"{x}"', self.properties[0].enum_values))}]"
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
class Parameter:
    name: str
    position: str
    description: str
    schema: Schema


class AuthType(enum.Enum):
    API_KEY = "apiKey"
    BASIC = "basic"
    BEARER = "bearer"
    OAUTH2 = "oauth2"
    COOKIE = "cookie"


@dataclass
class AuthSchema:
    type: str
    scheme: str


BEARER_AUTH = AuthSchema("http", "bearer")
BEARER_AUTH.bearerFormat = "JWT"

TOKEN_AUTH = AuthSchema("apiKey", "")
TOKEN_AUTH.name = "Authorization"
TOKEN_AUTH.position = "header"

BASIC_AUTH = AuthSchema("http", "basic")
SESSION_AUTH = AuthSchema("http", "cookie")

API_KEY_AUTH = AuthSchema("apiKey", "")
API_KEY_AUTH.position = "header"
API_KEY_AUTH.name = "X-API-KEY"

OAUTH2_AUTH = AuthSchema("oauth2", "")
OAUTH2_AUTH.authorizationUrl = ""
OAUTH2_AUTH.scopes = set()


@dataclass(slots=True)
class SecurityScheme:
    type: AuthType
    auth: AuthSchema


@dataclass(slots=True)
class Method:
    operation_id: str
    request_type: Literal["get", "post", "put", "delete"]
    request_schema: Schema
    response_schema: dict[str, ResponseSchema]
    tags: list[str]
    parameters: list[QueryParam]
    security_schemes: list[SecurityScheme]
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

    @property
    def contains_query_params(self) -> bool:
        """
        Query params means `?foo=bar&bar=foo` inside a url
        :return: true if the method contains query params, false otherwise
        """
        return any(param.position == "query" for param in self.parameters)


@dataclass(slots=True)
class ApiPath:
    path: str
    methods: list[Method]

    def get_path_params(self) -> list[str]:
        res = set()
        for method in self.methods:
            for param in method.parameters:
                if param.position == "path":
                    res.add(f"{convert_camel_case_to_snake_case(param.name)}: {param.schema.get_type_hint_str()}")
        return list(res)

    def get_dispatcher_params(self) -> str:
        res = set()
        if not self.methods:
            return ""
        for method in self.methods:
            for param in method.parameters:
                if param.position == "path":
                    res.add(f"<{param.schema.get_type_hint_str()}:{convert_camel_case_to_snake_case(param.name)}>")
        return "/".join(res)

    def get_dispatcher_name(self):
        sections = self.path.split("/")
        correct_sections = []
        for section in sections:
            if section.startswith("{"):
                continue
            correct_sections.append(section)
        return "/".join(correct_sections)


class OpenAPIDefinition:
    paths: list[ApiPath]
    # to check if a schema already exists which we can reuse directly
    created_schemas: dict[str, Schema]
    auth_schemes: dict[str, SecurityScheme]
    parameter_schemas: dict[str, Parameter]
    response_schemas: dict[str, Schema]
    __openapi_data: dict

    __slots__ = ("paths", "created_schemas", "auth_schemes", "__openapi_data", "parameter_schemas", "response_schemas")

    def __init__(self, yaml_data: dict):
        self.__openapi_data = yaml_data
        self.created_schemas = {}
        self.auth_schemes = {}
        self.paths = []
        self.parameter_schemas = {}
        self.response_schemas = {}

    @property
    def openapi_data(self):
        return self.__openapi_data

    def parse(self):
        self._extract_security_schemes()
        self._extract_schemas()
        self._extract_paths()
        self._extract_parameter_schemas()

    def _extract_schemas(self):
        required_schemas = self.__openapi_data["components"]["schemas"]
        for key, value in required_schemas.items():
            combined_schemas = defaultdict(tuple)
            if "type" not in value:
                combined_schemas = extract_combined_schemas(value, self)

            self.created_schemas[key] = Schema(
                name=key,
                properties=create_properties(value, self),
                typ=SchemaType(value["type"]),
                required_fields=set(value.get("required", [])),
            )

            if combined_schemas:
                self.created_schemas[key].combined_schemas = combined_schemas

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
                                type_=request_schema_def.get("type", ""),
                                enum_values=request_schema_def.get("enum", []),
                            )
                        ],
                        # TODO fix me
                        typ=SchemaType(request_schema_def.get("type", "object")),
                        required_fields=request_schema_def.get("required", []),
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
                                    if isinstance(val, dict):
                                        props.append(
                                            Property(
                                                name="",
                                                example=val.get("default"),
                                                type_=val.get("type"),
                                                enum_values=[],
                                            )
                                        )
                                    else:
                                        props.append(Property(name="", example=f'"{val}"', type_=list, enum_values=[]))
                                response_schema = ResponseSchema(
                                    required=True,
                                    type=SchemaType(resp_schema_typ),
                                    schema=Schema(
                                        name=request_schema_name,
                                        properties=props,
                                        typ=SchemaType("object"),
                                        required_fields=resp_content.get("required", []),
                                    ),
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
                parameters = create_parameters(data.get("parameters", []), self.created_schemas)
                if query_schema := create_schema_from_query_params(data["operationId"], parameters):
                    self.created_schemas[query_schema.name] = query_schema
                method_data.append(
                    Method(
                        operation_id=data["operationId"],
                        request_type=method,
                        request_schema=request_schema,
                        response_schema=response_schemas,
                        tags=data.get("tags", []),
                        parameters=parameters,
                        security_schemes=self._get_security_schemas(data.get("security", [])),
                    )
                )
            self.paths.append(
                ApiPath(
                    path=path,
                    methods=method_data,
                )
            )

    def _extract_security_schemes(self):
        security_schemes = self.__openapi_data.get("components", {}).get("securitySchemes", {})
        for name, scheme in security_schemes.items():
            match scheme["type"]:
                case "apiKey":
                    self.auth_schemes[name] = SecurityScheme(type=AuthType.API_KEY, auth=API_KEY_AUTH)
                    self.auth_schemes[name].auth.name = scheme.get("name", API_KEY_AUTH.name)
                case "basic":
                    self.auth_schemes[name] = SecurityScheme(type=AuthType.BASIC, auth=BASIC_AUTH)
                case "bearer":
                    self.auth_schemes[name] = SecurityScheme(type=AuthType.BEARER, auth=BEARER_AUTH)
                case "oauth2":
                    self.auth_schemes[name] = SecurityScheme(type=AuthType.OAUTH2, auth=OAUTH2_AUTH)
                    implicit_definition = scheme.get("flows", {}).get("implicit", {})
                    authorization_url = implicit_definition.get("authorizationUrl", "")
                    if authorization_url:
                        OAUTH2_AUTH.authorizationUrl = authorization_url
                    scopes = implicit_definition.get("scopes", {})
                    if scopes:
                        OAUTH2_AUTH.scopes = set(scopes.keys())
                case _:
                    print(f"Unknown security scheme: {name}")

    def _get_security_schemas(self, data: list) -> list[SecurityScheme]:
        res = []
        for scheme_definition in data:
            for scheme_name in scheme_definition.keys():
                try:
                    res.append(self.auth_schemes[scheme_name])
                except KeyError:
                    print(f"Unknown security scheme: {scheme_name}")
        return res

    def _extract_parameter_schemas(self):
        parameters_schemes: dict = self.__openapi_data.get("components", {}).get("parameters", {})
        for value in parameters_schemes.values():
            field_name = value.get("name")
            is_required = value.get("schema", {}).get("required", False)
            required_fields = set()
            if is_required:
                required_fields.add(field_name)
            self.parameter_schemas[field_name] = Parameter(
                name=field_name,
                position=value.get("in", ""),
                description=value.get("description", ""),
                schema=Schema(
                    name=field_name,
                    properties=[create_property(field_name, value["schema"], self)],
                    typ=SchemaType(value["schema"]["type"]),
                    required_fields=required_fields,
                ),
            )

    @staticmethod
    def extract_reference(definition: "OpenAPIDefinition", reference: str) -> Schema | None:
        try:
            *first, component_kind, name = reference.split("/")
        except (AttributeError, TypeError, ValueError):
            return None

        try:
            data = definition.openapi_data["components"][component_kind][name]
        except KeyError:
            return None

        combined_schemas = defaultdict(tuple)

        if "type" not in data:
            combined_schemas = extract_combined_schemas(data, definition)

        if combined_schemas:
            schema = Schema(
                name=name,
                properties={},
                typ=SchemaType.OBJECT,
                required_fields=set(data.get("required", [])),
            )
            schema.combined_schemas = combined_schemas
        else:
            schema = Schema(
                name=name,
                properties=create_properties(data, definition),
                typ=SchemaType(data["type"]),
                required_fields=set(data.get("required", [])),
            )
            definition.created_schemas[name] = schema

        return schema


def extract_combined_schemas(data: dict, definition: OpenAPIDefinition) -> dict[str, tuple[Schema | dict | None, ...]]:
    combined_schemas = defaultdict(tuple)
    if "discriminator" in data:
        combined_schemas["discriminator"] = (data["discriminator"],)
    for obj in ("oneOf", "anyOf", "allOf"):
        if obj in data:
            for elem in data[obj]:
                if "$ref" in elem:
                    schema_obj = OpenAPIDefinition.extract_reference(definition, elem["$ref"])
                    combined_schemas[obj] = (*combined_schemas[obj], schema_obj)
                else:
                    schema_obj = create_schema_from_data(elem, definition)
                    combined_schemas[obj] = (*combined_schemas[obj], schema_obj)
    return combined_schemas


def create_schema_from_data(data: dict, definition: OpenAPIDefinition) -> Schema:
    return Schema(
        name="",
        properties=create_properties(data, definition),
        typ=SchemaType(data["type"]),
        required_fields=set(data.get("required", [])),
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
        return
    else:
        if isinstance(val, dict):
            return Property(name="", example="", type_=convert_type(val.get("type")), enum_values=[])
        return Property(name="", example="", type_=convert_type(val), enum_values=[])


def create_property(name: str, data: dict, definition: OpenAPIDefinition) -> Property:
    data_type: Optional[str] = data.get("type", None)

    prop = Property(
        name=name,
        example=data.get("example"),
        type_=convert_type(data_type or "", data.get("format")),
        enum_values=data.get("enum", []),
    )
    if prop.enum_values:
        prop.type = enum.Enum
    if prop.type == list:
        item_ref = data.get("items").get("$ref")
        prop.ref = OpenAPIDefinition.extract_reference(definition, item_ref)
    if "$ref" in data:
        prop.ref = OpenAPIDefinition.extract_reference(definition, data["$ref"])

    if data_type:
        for attribute in ADDITIONAL_PROPERTIES.get(data_type, []):
            if attribute in data:
                prop.additional_requirements[attribute] = data[attribute]

    return prop


def create_properties(data: dict, definition: OpenAPIDefinition) -> list[Property]:
    return [create_property(key, value, definition) for key, value in data.get("properties", {}).items()]


def create_parameters(data: list, existing_schemas: dict = {}) -> list[QueryParam]:
    res: list[QueryParam] = []

    for obj in data:
        properties = []
        prop = Property(
            name="",
            example=obj["schema"].get("example"),
            type_=convert_type(obj["schema"].get("type", ""), obj["schema"].get("format")),
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
                schema=Schema(
                    name="",
                    properties=properties,
                    typ=SchemaType(obj["schema"].get("type", "object")),
                    required_fields=set(),
                ),
            ),
        )

    return res


def create_schema_from_query_params(operation_id: str, params: list[QueryParam]) -> Schema | None:
    schema = Schema(name=f"{to_class_name(operation_id)}", properties=[], typ=SchemaType.OBJECT, required_fields=set())
    for param in params:
        if param.position != "query":
            continue
        schema.properties.append(
            Property(
                name=param.name,
                example=param.schema.properties[0].example,
                type_=param.schema.properties[0].type,
                enum_values=param.schema.properties[0].enum_values,
                ref=param.schema.properties[0].ref,
            )
        )
    if schema.properties:
        return schema
    return None
