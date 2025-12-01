from pathlib import Path
from string import Template
from typing import Optional

from openapi_reader.schema import (
    OpenAPIDefinition,
    Property,
    AuthType,
    ResponseSchema,
    SchemaType,
    Method,
    ApiPath,
    SecurityScheme,
)
from openapi_reader.utils import (
    write_data_to_file,
    INDENT,
    operation_id_to_function_name,
)

BASE_IMPORTS = {
    "import datetime as dt",
    "import typing",
    "from fastapi import FastAPI, HTTPException",
}

SECURITY_DEFINITIONS = set()

SERIALIZER_FILE_NAME = "serializers"
VIEW_FILE_NAME = "views"

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

    write_data_to_file(
        schemas,
        import_statements=SERIALIZER_IMPORT,
        file_name="serializers",
        export_folder=export_folder,
        use_tempdir=use_tempdir,
    )


async_request_template = Template("""
@app.$http_kind("$path", status_code=$response_success_status_code)
async def $function_name($params) -> $result:
    if True:
        return $response_success
    else:
        raise HTTPException(status_code=$response_error_status_code)
""")

api_key_template = Template("""
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=True)

def get_api_key(api_key: str = Security(api_key_header)):
    # TODO: Check api_key against your database or other secure storage
    if api_key != "expected_key":
        raise HTTPException(
            status_code=403,
            detail="Could not validate credentials"
        )
    return api_key
    
APIKeyDep = Annotated[str, Security(get_api_key)]
""")

basic_auth_template = Template("""
security_basic = HTTPBasic()

def get_current_username(credentials: HTTPBasicCredentials = Security(security_basic)):
    # credentials.username and credentials.password are available here
    # TODO: Check credentials against your database or other secure storage
    if credentials.username != "" or credentials.password != "":
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return credentials.username

BasicDep = Annotated[str, Security(get_current_username)]
""")

bearer_auth_template = Template("""
security_bearer = HTTPBearer()

def get_current_token(credentials: HTTPAuthorizationCredentials = Security(security_bearer)):
    # credentials.scheme is "Bearer"
    # credentials.credentials is the actual token string
    token = credentials.credentials
    # TODO: Check token against your database or other secure storage
    if token != "valid-token":
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return token
    
BearerDep = Annotated[str, Security(get_current_token)]
""")

oauth2_template = Template("""
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="$tokenUrl")

def get_oauth2_token(token: str = Depends(oauth2_scheme)):
    # Decode token here (e.g., using python-jose or pyjwt)
    # TODO: Check token against your database or other secure storage
    if token != "valid-token":
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return token
    
OAuth2Dep = Annotated[str, Depends(get_oauth2_token)]
""")

oauth2_scoped_template = Template("""
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="$tokenUrl", scopes=$scopes)

def get_oauth2_scoped_token(security_scopes: SecurityScopes, token: str = Depends(oauth2_scheme)):
    # 1. Get scopes required by the endpoint (e.g., ["items:read"])
    required_scopes = security_scopes.scopes
    
    # 2. Decode token (pseudocode)
    # payload = jwt.decode(token, ...)
    # TODO: Check token against your database or other secure storage
    if token != "valid-token":
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    # token_scopes = payload.get("scopes", [])
    
    # TODO remove
    token_scopes = ["items:read"] 
    
    # 3. Validate
    for scope in required_scopes:
        if scope not in token_scopes:
            raise HTTPException(
                status_code=401,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": f'Bearer scope="{security_scopes.scope_str}'},
            )

    return token
""")

cookie_auth_template = Template("""
cookie_scheme = APIKeyCookie(name="session_id")

def get_cookie_session(session_id: str = Security(cookie_scheme)):
    if not session_id:
         raise HTTPException(status_code=403, detail="No session found")
    return session_id
    
CookieDep = Annotated[str, Security(get_cookie_session)]
""")

SECURITY_IMPORTS = {
    AuthType.API_KEY: "from fastapi import Security\nfrom fastapi.security import APIKeyHeader",
    AuthType.BASIC: "from fastapi.security import HTTPBasic, HTTPBasicCredentials",
    AuthType.BEARER: "from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials",
    AuthType.OAUTH2: "from fastapi.security import OAuth2PasswordBearer",
    AuthType.COOKIE: "from fastapi.security import APIKeyCookie",
}

SECURITY_PARAMS = {
    AuthType.API_KEY: "key: APIKeyDep",
    AuthType.BASIC: "user: BasicDep",
    AuthType.BEARER: "token: BearerDep",
    AuthType.OAUTH2: "token: OAuth2Dep",
    AuthType.COOKIE: "session_id: CookieDep",
}


def create_request_and_response_objects(path: ApiPath, method: Method, security_scopes: list[SecurityScheme]) -> str:
    response_schema: Optional[ResponseSchema] = method.get_success_response_schema()
    success_error_code = method.get_success_error_code()
    fail_error_code = method.get_fail_error_code()

    query_params = []
    if security_scopes:
        for auth_ in security_scopes:
            match auth_.type:
                case AuthType.API_KEY:
                    SECURITY_DEFINITIONS.add(api_key_template.substitute())
                case AuthType.BASIC:
                    SECURITY_DEFINITIONS.add(basic_auth_template.substitute())
                case AuthType.BEARER:
                    SECURITY_DEFINITIONS.add(bearer_auth_template.substitute())
                case AuthType.COOKIE:
                    SECURITY_DEFINITIONS.add(cookie_auth_template.substitute())
                case _:
                    pass
            BASE_IMPORTS.add(SECURITY_IMPORTS[auth_.type])
            BASE_IMPORTS.add("from fastapi import Depends")
            BASE_IMPORTS.add("from fastapi import Annotated")
            if auth_.type == AuthType.OAUTH2:
                if hasattr(auth_.auth, "scopes"):
                    scopes = [f'"{obj}"' for obj in auth_.auth.scopes]
                    BASE_IMPORTS.add("from fastapi import SecurityScopes")
                    SECURITY_DEFINITIONS.add(
                        oauth2_scoped_template.substitute(
                            tokenUrl=auth_.auth.authorizationUrl, scopes=f"[{', '.join(scopes)}]"
                        )
                    )
                    query_params.append(
                        f"token: Annotated[str, Security(get_oauth2_scoped_token, scopes=[{', '.join(scopes)}])]"
                    )
                else:
                    SECURITY_DEFINITIONS.add(oauth2_template.substitute(tokenUrl=auth_.auth.authorizationUrl))
                    query_params.append(SECURITY_PARAMS[auth_.type])
            else:
                query_params.append(SECURITY_PARAMS[auth_.type])
    if method.contains_query_params:
        query_params = [f"{obj.name}: {obj.schema.get_type_hint_str()}" for obj in method.parameters]

    response_txt = "typing.Any"
    response_success = "None"

    if response_schema:
        if response_schema.type == SchemaType.OBJECT and response_schema.schema.name:
            BASE_IMPORTS.add(f"from .{SERIALIZER_FILE_NAME} import {response_schema.schema.name}")
        if response_schema.type == SchemaType.ARRAY.value:
            response_txt = f"list[{response_schema.schema.name}]"
            response_success = f"[{response_schema.schema.name}()]"
        else:
            response_txt = response_schema.schema.name if response_schema.schema.name else "None"
            response_success = f"{response_schema.schema.name}()" if response_schema.schema.name else "None"

    match method.request_type:
        case "get":
            return async_request_template.substitute(
                http_kind="get",
                path=path.path,
                function_name=operation_id_to_function_name(method.operation_id),
                params=", ".join(query_params) if query_params else "",
                result=response_txt,
                response_success=response_success,
                response_success_status_code=success_error_code,
                response_error_status_code=fail_error_code,
            )
        case "post":
            return async_request_template.substitute(
                http_kind="post",
                path=path.path,
                function_name=operation_id_to_function_name(method.operation_id),
                params=", ".join(query_params) if query_params else "",
                result=response_txt,
                response_success=response_success,
                response_success_status_code=success_error_code,
                response_error_status_code=fail_error_code,
            )
        case "put":
            return async_request_template.substitute(
                http_kind="put",
                path=path.path,
                function_name=operation_id_to_function_name(method.operation_id),
                params=", ".join(query_params) if query_params else "",
                result=response_txt,
                response_success=response_success,
                response_success_status_code=success_error_code,
                response_error_status_code=fail_error_code,
            )
        case "patch":
            return async_request_template.substitute(
                http_kind="patch",
                path=path.path,
                function_name=operation_id_to_function_name(method.operation_id),
                params=", ".join(query_params) if query_params else "",
                result=response_txt,
                response_success=response_success,
                response_success_status_code=success_error_code,
                response_error_status_code=fail_error_code,
            )
        case "delete":
            return async_request_template.substitute(
                http_kind="delete",
                path=path.path,
                function_name=operation_id_to_function_name(method.operation_id),
                params=", ".join(query_params) if query_params else "",
                result=response_txt,
                response_success=response_success,
                response_success_status_code=success_error_code,
                response_error_status_code=fail_error_code,
            )


def create_view_func(path) -> str:
    functions = []
    for method in path.methods:
        security_checks = []

        for security_schema in method.security_schemes:
            security_checks.append(security_schema)

        func_txt = create_request_and_response_objects(path, method, security_checks)
        functions.append(func_txt)

    return "\n".join(functions)


def create_view_file(
    definition: OpenAPIDefinition, *, export_folder: Optional[Path] = None, use_tempdir: bool = False
) -> None:
    views = ["app = FastAPI()", "\n"]
    for path in definition.paths:
        views.append(create_view_func(path))

    write_data_to_file(
        views,
        import_statements=list(BASE_IMPORTS) + list(SECURITY_DEFINITIONS),
        file_name=VIEW_FILE_NAME,
        export_folder=export_folder,
        use_tempdir=use_tempdir,
    )
