from pathlib import Path
from string import Template
from typing import Optional

from py_openapi_tools.schema import (
    OpenAPIDefinition,
    Schema,
    Property,
    Method,
    ResponseSchema,
    SchemaType,
    ApiPath,
    AuthType,
    ADDITIONAL_PROPERTIES,
    PYTHON_TYPE_MAPPING,
)
from py_openapi_tools.utils import (
    HTTPResponse,
    convert_camel_case_to_snake_case,
    to_class_name,
    write_data_to_file,
    INDENT,
)

SERIALIZERS = {
    "str": "serializers.CharField",
    "email": "serializers.EmailField",
    "datetime": "serializers.DateTimeField",
    "int": "serializers.IntegerField",
    "float": "serializers.FloatField",
    "enum": "serializers.CharField",
    "bool": "serializers.BooleanField",
    "regex": "serializers.RegexField",
}

INITIAL_FILE_INPUTS = ["from rest_framework import serializers"]
INITIAL_VIEW_FILE_INPUTS = [
    "import typing",
    "from django.http import HttpResponse",
    "from rest_framework.response import Response",
    "from rest_framework import status as drf_status",
    "from rest_framework.views import APIView",
    "from rest_framework.permissions import IsAuthenticated",
    "from rest_framework.decorators import api_view",
    "from django.db import IntegrityError",
    "from rest_framework.serializers import Serializer",
    "from serializers import *",
]


def to_drf_status_code(code: HTTPResponse) -> str:
    match code:
        case HTTPResponse.OK:
            return "drf_status.HTTP_200_OK"
        case HTTPResponse.CREATED:
            return "drf_status.HTTP_201_CREATED"
        case HTTPResponse.ACCEPTED:
            return "drf_status.HTTP_202_ACCEPTED"
        case HTTPResponse.NO_CONTENT:
            return "drf_status.HTTP_204_NO_CONTENT"
        case HTTPResponse.RESET_CONTENT:
            return "drf_status.HTTP_205_RESET_CONTENT"
        case HTTPResponse.PARTIAL_CONTENT:
            return "drf_status.HTTP_206_PARTIAL_CONTENT"
        case HTTPResponse.MULTI_STATUS:
            return "drf_status.HTTP_207_MULTI_STATUS"
        case HTTPResponse.ALREADY_REPORTED:
            return "drf_status.HTTP_208_ALREADY_REPORTED"
        case HTTPResponse.IM_USED:
            return "drf_status.HTTP_226_IM_USED"
        case HTTPResponse.MULTIPLE_CHOICES:
            return "drf_status.HTTP_300_MULTIPLE_CHOICES"
        case HTTPResponse.MOVED_PERMANENTLY:
            return "drf_status.HTTP_301_MOVED_PERMANENTLY"
        case HTTPResponse.FOUND:
            return "drf_status.HTTP_302_FOUND"
        case HTTPResponse.SEE_OTHER:
            return "drf_status.HTTP_303_SEE_OTHER"
        case HTTPResponse.NOT_MODIFIED:
            return "drf_status.HTTP_304_NOT_MODIFIED"
        case HTTPResponse.USE_PROXY:
            return "drf_status.HTTP_305_USE_PROXY"
        case HTTPResponse.TEMPORARY_REDIRECT:
            return "drf_status.HTTP_307_TEMPORARY_REDIRECT"
        case HTTPResponse.PERMANENT_REDIRECT:
            return "drf_status.HTTP_308_PERMANENT_REDIRECT"
        case HTTPResponse.BAD_REQUEST:
            return "drf_status.HTTP_400_BAD_REQUEST"
        case HTTPResponse.UNAUTHORIZED:
            return "drf_status.HTTP_401_UNAUTHORIZED"
        case HTTPResponse.FORBIDDEN:
            return "drf_status.HTTP_403_FORBIDDEN"
        case HTTPResponse.NOT_FOUND:
            return "drf_status.HTTP_404_NOT_FOUND"
        case HTTPResponse.METHOD_NOT_ALLOWED:
            return "drf_status.HTTP_405_METHOD_NOT_ALLOWED"
        case HTTPResponse.NOT_ACCEPTABLE:
            return "drf_status.HTTP_406_NOT_ACCEPTABLE"
        case HTTPResponse.PROXY_AUTHENTICATION_REQUIRED:
            return "drf_status.HTTP_407_PROXY_AUTHENTICATION_REQUIRED"
        case HTTPResponse.REQUEST_TIMEOUT:
            return "drf_status.HTTP_408_REQUEST_TIMEOUT"
        case HTTPResponse.CONFLICT:
            return "drf_status.HTTP_409_CONFLICT"
        case HTTPResponse.GONE:
            return "drf_status.HTTP_410_GONE"
        case HTTPResponse.LENGTH_REQUIRED:
            return "drf_status.HTTP_411_LENGTH_REQUIRED"
        case HTTPResponse.PRECONDITION_FAILED:
            return "drf_status.HTTP_412_PRECONDITION_FAILED"
        case HTTPResponse.REQUEST_ENTITY_TOO_LARGE:
            return "drf_status.HTTP_413_REQUEST_ENTITY_TOO_LARGE"
        case HTTPResponse.REQUEST_URI_TOO_LONG:
            return "drf_status.HTTP_414_REQUEST_URI_TOO_LONG"
        case HTTPResponse.UNSUPPORTED_MEDIA_TYPE:
            return "drf_status.HTTP_415_UNSUPPORTED_MEDIA_TYPE"
        case HTTPResponse.REQUESTED_RANGE_NOT_SATISFIABLE:
            return "drf_status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE"
        case HTTPResponse.EXPECTATION_FAILED:
            return "drf_status.HTTP_417_EXPECTATION_FAILED"
        case HTTPResponse.IM_A_TEAPOT:
            return "drf_status.HTTP_418_IM_A_TEAPOT"
        case HTTPResponse.MISDIRECTED_REQUEST:
            return "drf_status.HTTP_421_MISDIRECTED_REQUEST"
        case HTTPResponse.UNPROCESSABLE_ENTITY:
            return "drf_status.HTTP_422_UNPROCESSABLE_ENTITY"
        case HTTPResponse.LOCKED:
            return "drf_status.HTTP_423_LOCKED"
        case HTTPResponse.FAILED_DEPENDENCY:
            return "drf_status.HTTP_424_FAILED_DEPENDENCY"
        case HTTPResponse.UPGRADE_REQUIRED:
            return "drf_status.HTTP_426_UPGRADE_REQUIRED"
        case HTTPResponse.PRECONDITION_REQUIRED:
            return "drf_status.HTTP_428_PRECONDITION_REQUIRED"
        case HTTPResponse.TOO_MANY_REQUESTS:
            return "drf_status.HTTP_429_TOO_MANY_REQUESTS"
        case HTTPResponse.REQUEST_HEADER_FIELDS_TOO_LARGE:
            return "drf_status.HTTP_431_REQUEST_HEADER_FIELDS_TOO_LARGE"
        case HTTPResponse.UNAVAILABLE_FOR_LEGAL_REASONS:
            return "drf_status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS"
        case HTTPResponse.INTERNAL_SERVER_ERROR:
            return "drf_status.HTTP_500_INTERNAL_SERVER_ERROR"
        case HTTPResponse.NOT_IMPLEMENTED:
            return "drf_status.HTTP_501_NOT_IMPLEMENTED"
        case HTTPResponse.BAD_GATEWAY:
            return "drf_status.HTTP_502_BAD_GATEWAY"
        case HTTPResponse.SERVICE_UNAVAILABLE:
            return "drf_status.HTTP_503_SERVICE_UNAVAILABLE"
        case HTTPResponse.GATEWAY_TIMEOUT:
            return "drf_status.HTTP_504_GATEWAY_TIMEOUT"
        case HTTPResponse.HTTP_VERSION_NOT_SUPPORTED:
            return "drf_status.HTTP_505_HTTP_VERSION_NOT_SUPPORTED"
        case HTTPResponse.VARIANT_ALSO_NEGOTIATES:
            return "drf_status.HTTP_506_VARIANT_ALSO_NEGOTIATES"
        case HTTPResponse.INSUFFICIENT_STORAGE:
            return "drf_status.HTTP_507_INSUFFICIENT_STORAGE"
        case HTTPResponse.LOOP_DETECTED:
            return "drf_status.HTTP_508_LOOP_DETECTED"
        case HTTPResponse.NOT_EXTENDED:
            return "drf_status.HTTP_510_NOT_EXTENDED"
        case HTTPResponse.NETWORK_AUTHENTICATION_REQUIRED:
            return "drf_status.HTTP_511_NETWORK_AUTHENTICATION_REQUIRED"
        case _:
            return ""


def create_serializer_additional_parameters(prop: Property) -> list[str] | None:
    function_params = []
    if not hasattr(prop.type, "__name__"):
        return None
    for elem in ADDITIONAL_PROPERTIES.get(PYTHON_TYPE_MAPPING.get(prop.type, ""), []):
        if data := prop.additional_requirements.get(elem):
            function_params.append(f"{convert_camel_case_to_snake_case(elem)}={data}")

    if function_params:
        return function_params
    return None


def serializer_func_from_property_type(prop: Property) -> str:
    serializer_class = ""
    function_params = []
    function_params_str = "()"

    if not hasattr(prop.type, "__name__"):
        if prop.ref:
            if prop.ref.properties:
                serializer_class = f"{prop.ref.name}Serializer"
            else:
                try:
                    serializer_class = SERIALIZERS.get(prop.ref.typ.to_python_type().__name__.lower(), "str")
                except AttributeError:
                    return "None"
        else:
            print(f"Unknown property type: {prop}")
            return "None"
    else:
        if additional_params := create_serializer_additional_parameters(prop):
            function_params.extend(additional_params)
        if function_params:
            function_params_str = f"({', '.join(function_params)})"

        match prop.type.__name__.lower():
            case "list":
                if hasattr(prop.ref, "name") and prop.ref.name:
                    function_params.append("many=True")
                    serializer_class = f"{prop.ref.name.title()}Serializer"
                elif isinstance(prop.ref, Property):
                    return f"serializers.ListField(child={SERIALIZERS[prop.ref.type.__name__.lower()]}{function_params_str})"
                else:
                    try:
                        serializer_class = SERIALIZERS[prop.ref.properties[0].type.__name__.lower()]
                    except AttributeError:
                        serializer_class = "serializers.ListField"
            case "str":
                if prop.example and ("@" in prop.example or "email" in prop.name):
                    serializer_class = SERIALIZERS["email"]
                elif "pattern" in prop.additional_requirements:
                    data = {obj[0]: obj[1] for obj in [val.split("=") for val in function_params]}
                    function_params = [f"{key}={val}" for key, val in data.items() if key != "pattern"]
                    function_params[0] = data["pattern"]
                    function_params_str = f"({', '.join(function_params)})"
                    serializer_class = SERIALIZERS["regex"]
                else:
                    serializer_class = SERIALIZERS["str"]
            case "datetime" | "date":
                serializer_class = SERIALIZERS["datetime"]
            case "int":
                serializer_class = SERIALIZERS["int"]
            case "float":
                serializer_class = SERIALIZERS["float"]
            case "enum" | "Enum":
                serializer_class = SERIALIZERS["enum"]
            case "bool":
                serializer_class = SERIALIZERS["bool"]
            case _:
                if prop.ref:
                    serializer_class = f"{prop.ref.name.title()}Serializer"
                else:
                    serializer_class = "None"
    return f"{serializer_class}{function_params_str}"


def schema_to_drf(schema_name: str, schema: Schema) -> str:
    """
    Converts the openapi schema to the body of a Serializer class from django-rest-framework
    :param schema_name: the name of the schema, used for the class name
    :param schema: a Schema object from the openapi definition
    :return: the string body for django-rest-framework serializer class
    """

    if not schema.properties and not schema.combined_schemas:
        return ""

    properties: list[str] = []
    for prop in schema.properties:
        properties.append(f"{prop.name.lower()} = {serializer_func_from_property_type(prop)}")

    class_inheritance: list[str] = []
    if schema.combined_schemas and "allOf" in schema.combined_schemas:
        for combined_schema in schema.combined_schemas["allOf"]:
            if combined_schema.name:
                class_inheritance.append(combined_schema.name + "Serializer")
            else:
                for prop in combined_schema.properties:
                    properties.append(f"{prop.name.lower()} = {serializer_func_from_property_type(prop)}")
    else:
        class_inheritance.append("serializers.Serializer")

    class_inheritance_str = ", ".join(class_inheritance)

    schema_body = f"\n{INDENT}".join(properties)
    if not schema_body:
        schema_body = "pass"

    return f"""
class {schema_name}Serializer({class_inheritance_str}):
    {schema_body}
    """


# maybe return path to file instead of `None`
def create_serializer_file(
    definition: OpenAPIDefinition, *, export_folder: Optional[Path] = None, use_tempdir: bool = False
) -> None:
    schemas: list[str] = []
    for schema_name, schema in definition.created_schemas.items():
        schema_def = schema_to_drf(schema_name, schema)
        if not schema_def:
            continue

        if refs := schema.get_refs():
            min_idx = len(schemas)
            for ref in refs:
                if ref:
                    for idx, obj in enumerate(schemas):
                        if ref in obj:
                            min_idx = max(min_idx, idx)

            schemas.insert(min_idx + 1, schema_def)
        else:
            if "serializers.Serializer" not in schema_def:
                schemas.append(schema_def)
            else:
                schemas.insert(0, schema_def)

    write_data_to_file(
        schemas,
        import_statements=INITIAL_FILE_INPUTS,
        file_name="serializers",
        export_folder=export_folder,
        use_tempdir=use_tempdir,
    )


get_request_template = Template("""
    if request.method == "GET":
        $security
        $data
        $serializer
        return Response(serializer.data)
""")

"""
serializer = SnippetSerializer(data=request.data)
"""
post_request_template = Template("""
    if request.method == "POST":
        $security
        $serializer
        if serializer.is_valid():
            serializer.save()
            $response_success
        $response_error
""")

put_request_template = Template("""
    if request.method == "PUT":
        $security
        $serializer
        if serializer.is_valid():
            serializer.save()
            $response_success
        $response_error
""")

patch_request_template = Template("""
    if request.method == "PATCH":
        $security
        $serializer
        if serializer.is_valid():
            serializer.save()
            $response_success
        $response_error
""")

delete_request_template = Template("""
    if request.method == "DELETE":
        $security
        $serializer
        try:
            obj.delete()
        except IntegrityError:
            $response_error
        else:
            $response_success
""")


def create_request_and_response_objects(method: Method, security_scopes: list[str]) -> str:
    func_txt = ""
    security = ""
    if security_scopes:
        scopes = [f'"{scope_}"' for scope_ in security_scopes]
        security = f'if hasattr(request.auth, "is_valid") and not request.auth.is_valid({",".join(scopes)}):'
        security += f"{INDENT * 2}return Response(status=drf_status.HTTP_401_UNAUTHORIZED)"
    response_schema: Optional[ResponseSchema] = method.get_success_response_schema()
    success_error_code = method.get_success_error_code()
    fail_error_code = method.get_fail_error_code()
    match method.request_type:
        case "get":
            if response_schema:
                if response_schema.type == SchemaType.ARRAY.value:
                    example_data = "values = []"
                    schema_txt = f"serializer = {response_schema.schema.name}Serializer(values, many=True)"
                else:
                    example_data = "data = {}"
                    schema_txt = f"serializer = {response_schema.schema.name}Serializer(data)"
                if method.contains_query_params:
                    example_data = f"""
        serializer = {to_class_name(method.operation_id)}Serializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status={to_drf_status_code(fail_error_code)})
        
        {example_data}
"""

                func_txt = get_request_template.substitute(security=security, data=example_data, serializer=schema_txt)
        case "post":
            request_schema = method.request_schema
            if request_schema.name:
                request_schema_txt = f"serializer = {request_schema.name}Serializer(data=request.data)"
            elif method.contains_query_params:
                request_schema_txt = (
                    f"serializer = {to_class_name(method.operation_id)}Serializer(data=request.query_params)"
                )
            else:
                request_schema_txt = "serializer = Serializer(data=request.data)"
            success_response_txt = f"return Response(serializer.data, status={to_drf_status_code(success_error_code)})"
            error_response_txt = f"return Response(serializer.errors, status={to_drf_status_code(fail_error_code)})"
            func_txt = post_request_template.substitute(
                security=security,
                serializer=request_schema_txt,
                response_success=success_response_txt,
                response_error=error_response_txt,
            )
        case "put":
            request_schema = method.request_schema
            request_schema_txt = f"serializer = {request_schema.name}Serializer(data=request.data)"
            success_response_txt = f"return Response(serializer.data, status={to_drf_status_code(success_error_code)})"
            error_response_txt = f"return Response(serializer.errors, status={to_drf_status_code(fail_error_code)})"
            func_txt = put_request_template.substitute(
                security=security,
                serializer=request_schema_txt,
                response_success=success_response_txt,
                response_error=error_response_txt,
            )
        case "patch":
            request_schema = method.request_schema
            request_schema_txt = f"serializer = {request_schema.name}Serializer(data=request.data)"
            success_response_txt = f"return Response(serializer.data, status={to_drf_status_code(success_error_code)})"
            error_response_txt = f"return Response(serializer.errors, status={to_drf_status_code(fail_error_code)})"
            func_txt = patch_request_template.substitute(
                security=security,
                serializer=request_schema_txt,
                response_success=success_response_txt,
                response_error=error_response_txt,
            )
        case "delete":
            if method.contains_query_params:
                serializer_txt = f"obj = {to_class_name(method.operation_id)}Serializer(data=request.query_params)"
            else:
                serializer_txt = f"#TODO replace me\n{INDENT}{INDENT}obj = Serializer()"
            success_response_txt = f"return HttpResponse(status={to_drf_status_code(success_error_code)})"
            error_response_txt = f"return HttpResponse(status={to_drf_status_code(fail_error_code)})"
            func_txt = delete_request_template.substitute(
                security=security,
                serializer=serializer_txt,
                response_success=success_response_txt,
                response_error=error_response_txt,
            )

    return func_txt


def create_view_func(path: ApiPath) -> str:
    function_name = convert_camel_case_to_snake_case(path.methods[0].operation_id)
    api_requests = [f'"{obj.request_type.upper()}"' for obj in path.methods]
    api_decorator_txt = f"@api_view([{', '.join(api_requests)}])"
    functions = []
    authentication_schemes = set()
    permission_classes = set()
    for method in path.methods:
        security_checks = []

        for security_schema in method.security_schemes:
            permission_classes.add("IsAuthenticated")
            match security_schema.type:
                case AuthType.API_KEY | AuthType.BEARER:
                    if "from rest_framework.authentication import TokenAuthentication" not in INITIAL_VIEW_FILE_INPUTS:
                        INITIAL_VIEW_FILE_INPUTS.append("from rest_framework.authentication import TokenAuthentication")
                    authentication_schemes.add("TokenAuthentication")
                case AuthType.BASIC:
                    if "from rest_framework.authentication import BasicAuthentication" not in INITIAL_VIEW_FILE_INPUTS:
                        INITIAL_VIEW_FILE_INPUTS.append("from rest_framework.authentication import BasicAuthentication")
                    authentication_schemes.add("BasicAuthentication")
                case AuthType.OAUTH2:
                    if (
                        "from oauth2_provider.contrib.rest_framework import OAuth2Authentication"
                        not in INITIAL_VIEW_FILE_INPUTS
                    ):
                        INITIAL_VIEW_FILE_INPUTS.append(
                            "from oauth2_provider.contrib.rest_framework import OAuth2Authentication"
                        )
                    # Optional: Add scope handling imports if your OpenAPI spec defines scopes
                    if (
                        "from oauth2_provider.contrib.rest_framework import TokenHasReadWriteScope"
                        not in INITIAL_VIEW_FILE_INPUTS
                    ):
                        INITIAL_VIEW_FILE_INPUTS.append(
                            "from oauth2_provider.contrib.rest_framework import TokenHasReadWriteScope"
                        )

                    authentication_schemes.add("OAuth2Authentication")
                    permission_classes.add("TokenHasReadWriteScope")
                    if hasattr(security_schema.auth, "scopes"):
                        security_checks = list(security_schema.auth.scopes)

        func_txt = create_request_and_response_objects(method, security_checks)
        if len(functions) > 1:
            func_txt.replace("if", "else if", 1)
        functions.append(func_txt)
    function_txt = "\n".join(functions)

    query_params = "request"
    if params := path.get_path_params():
        query_params += ", "
        query_params += ", ".join(params)

    if authentication_schemes:
        INITIAL_VIEW_FILE_INPUTS.append("from rest_framework.permissions import IsAuthenticated")
        INITIAL_VIEW_FILE_INPUTS.append(
            "from rest_framework.decorators import authentication_classes, permission_classes"
        )
        api_decorator_txt = f"{api_decorator_txt}\n@authentication_classes([{', '.join(authentication_schemes)}])"
        api_decorator_txt = f"{api_decorator_txt}\n@permission_classes([{', '.join(permission_classes)}])"

    view_func_txt = f"""
{api_decorator_txt}
def {function_name}({query_params}):
{function_txt}

    return HttpResponse(status=drf_status.HTTP_400_BAD_REQUEST)
"""
    return view_func_txt


def create_view_file(
    open_API: OpenAPIDefinition, *, export_folder: Optional[Path] = None, use_tempdir: bool = False
) -> None:  # noqa: C0103
    views = []
    for path in open_API.paths:
        views.append(create_view_func(path))

    write_data_to_file(
        views,
        import_statements=INITIAL_VIEW_FILE_INPUTS,
        file_name="views",
        export_folder=export_folder,
        use_tempdir=use_tempdir,
    )


ROUTER_BASE_IMPORT = ["from django.urls import path"]


def create_route(path: ApiPath) -> tuple[str, str]:
    function_name = convert_camel_case_to_snake_case(path.methods[0].operation_id)
    params: str = path.get_dispatcher_params()
    path_name: str = path.get_dispatcher_name()
    if params:
        return function_name, f"{path_name}/{params}/"
    return function_name, f"{path_name}/"


def create_urls_file(open_API: OpenAPIDefinition, *, export_folder: Optional[Path] = None, use_tempdir: bool = False):
    import_statements = ROUTER_BASE_IMPORT
    path_statements = ["urlpatterns = ["]
    for path in open_API.paths:
        view_name, _url = create_route(path)
        import_statements.append(f"from .views import {view_name}")
        path_statements.append(f"{INDENT}path('{_url}', {view_name}),")
    path_statements.append("]")

    write_data_to_file(
        path_statements,
        import_statements=import_statements,
        file_name="urls",
        export_folder=export_folder,
        use_tempdir=use_tempdir,
    )
