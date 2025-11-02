# function which creates serializer class with validators from a list `Schema` objects
# function which creates the request and response objects from a list of `Method` objects
from pathlib import Path
from string import Template
from typing import Optional
from unittest import case

import black
import isort

from openapi_reader.schema import OpenAPIDefinition, Schema, Property, Method, ResponseSchema, SchemaType, ApiPath
from openapi_reader.utils import HTTPResponse, convert_camel_case_to_snake_case

SERIALIZERS = {
    "str": "serializers.CharField()",  # can be extended
    "email": "serializers.EmailField()",
    "datetime": "serializers.DateTimeField()",
    "int": "serializers.IntegerField()",
    "float": "serializers.FloatField()",
    "enum": "serializers.CharField()",
    "bool": "serializers.BooleanField()",
}

INITIAL_FILE_INPUTS = ["from rest_framework import serializers"]
INITIAL_VIEW_FILE_INPUTS = [
    "from rest_framework.response import Response",
    "from rest_framework import status",
    "from rest_framework.views import APIView",
    "from rest_framework.permissions import IsAuthenticated",
    "from rest_framework.decorators import api_view",
    "from django.db import IntegrityError",
    "from rest_framework.serializers import Serializer",
    "from serializers import *",
]

INDENT = "    "


def to_drf_status_code(code: HTTPResponse) -> str:
    match code:
        case HTTPResponse.OK:
            return "status.HTTP_200_OK"
        case HTTPResponse.CREATED:
            return "status.HTTP_201_CREATED"
        case HTTPResponse.ACCEPTED:
            return "status.HTTP_202_ACCEPTED"
        case HTTPResponse.NO_CONTENT:
            return "status.HTTP_204_NO_CONTENT"
        case HTTPResponse.RESET_CONTENT:
            return "status.HTTP_205_RESET_CONTENT"
        case HTTPResponse.PARTIAL_CONTENT:
            return "status.HTTP_206_PARTIAL_CONTENT"
        case HTTPResponse.MULTI_STATUS:
            return "status.HTTP_207_MULTI_STATUS"
        case HTTPResponse.ALREADY_REPORTED:
            return "status.HTTP_208_ALREADY_REPORTED"
        case HTTPResponse.IM_USED:
            return "status.HTTP_226_IM_USED"
        case HTTPResponse.MULTIPLE_CHOICES:
            return "status.HTTP_300_MULTIPLE_CHOICES"
        case HTTPResponse.MOVED_PERMANENTLY:
            return "status.HTTP_301_MOVED_PERMANENTLY"
        case HTTPResponse.FOUND:
            return "status.HTTP_302_FOUND"
        case HTTPResponse.SEE_OTHER:
            return "status.HTTP_303_SEE_OTHER"
        case HTTPResponse.NOT_MODIFIED:
            return "status.HTTP_304_NOT_MODIFIED"
        case HTTPResponse.USE_PROXY:
            return "status.HTTP_305_USE_PROXY"
        case HTTPResponse.TEMPORARY_REDIRECT:
            return "status.HTTP_307_TEMPORARY_REDIRECT"
        case HTTPResponse.PERMANENT_REDIRECT:
            return "status.HTTP_308_PERMANENT_REDIRECT"
        case HTTPResponse.BAD_REQUEST:
            return "status.HTTP_400_BAD_REQUEST"
        case HTTPResponse.UNAUTHORIZED:
            return "status.HTTP_401_UNAUTHORIZED"
        case HTTPResponse.FORBIDDEN:
            return "status.HTTP_403_FORBIDDEN"
        case HTTPResponse.NOT_FOUND:
            return "status.HTTP_404_NOT_FOUND"
        case HTTPResponse.METHOD_NOT_ALLOWED:
            return "status.HTTP_405_METHOD_NOT_ALLOWED"
        case HTTPResponse.NOT_ACCEPTABLE:
            return "status.HTTP_406_NOT_ACCEPTABLE"
        case HTTPResponse.PROXY_AUTHENTICATION_REQUIRED:
            return "status.HTTP_407_PROXY_AUTHENTICATION_REQUIRED"
        case HTTPResponse.REQUEST_TIMEOUT:
            return "status.HTTP_408_REQUEST_TIMEOUT"
        case HTTPResponse.CONFLICT:
            return "status.HTTP_409_CONFLICT"
        case HTTPResponse.GONE:
            return "status.HTTP_410_GONE"
        case HTTPResponse.LENGTH_REQUIRED:
            return "status.HTTP_411_LENGTH_REQUIRED"
        case HTTPResponse.PRECONDITION_FAILED:
            return "status.HTTP_412_PRECONDITION_FAILED"
        case HTTPResponse.REQUEST_ENTITY_TOO_LARGE:
            return "status.HTTP_413_REQUEST_ENTITY_TOO_LARGE"
        case HTTPResponse.REQUEST_URI_TOO_LONG:
            return "status.HTTP_414_REQUEST_URI_TOO_LONG"
        case HTTPResponse.UNSUPPORTED_MEDIA_TYPE:
            return "status.HTTP_415_UNSUPPORTED_MEDIA_TYPE"
        case HTTPResponse.REQUESTED_RANGE_NOT_SATISFIABLE:
            return "status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE"
        case HTTPResponse.EXPECTATION_FAILED:
            return "status.HTTP_417_EXPECTATION_FAILED"
        case HTTPResponse.IM_A_TEAPOT:
            return "status.HTTP_418_IM_A_TEAPOT"
        case HTTPResponse.MISDIRECTED_REQUEST:
            return "status.HTTP_421_MISDIRECTED_REQUEST"
        case HTTPResponse.UNPROCESSABLE_ENTITY:
            return "status.HTTP_422_UNPROCESSABLE_ENTITY"
        case HTTPResponse.LOCKED:
            return "status.HTTP_423_LOCKED"
        case HTTPResponse.FAILED_DEPENDENCY:
            return "status.HTTP_424_FAILED_DEPENDENCY"
        case HTTPResponse.UPGRADE_REQUIRED:
            return "status.HTTP_426_UPGRADE_REQUIRED"
        case HTTPResponse.PRECONDITION_REQUIRED:
            return "status.HTTP_428_PRECONDITION_REQUIRED"
        case HTTPResponse.TOO_MANY_REQUESTS:
            return "status.HTTP_429_TOO_MANY_REQUESTS"
        case HTTPResponse.REQUEST_HEADER_FIELDS_TOO_LARGE:
            return "status.HTTP_431_REQUEST_HEADER_FIELDS_TOO_LARGE"
        case HTTPResponse.UNAVAILABLE_FOR_LEGAL_REASONS:
            return "status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS"
        case HTTPResponse.INTERNAL_SERVER_ERROR:
            return "status.HTTP_500_INTERNAL_SERVER_ERROR"
        case HTTPResponse.NOT_IMPLEMENTED:
            return "status.HTTP_501_NOT_IMPLEMENTED"
        case HTTPResponse.BAD_GATEWAY:
            return "status.HTTP_502_BAD_GATEWAY"
        case HTTPResponse.SERVICE_UNAVAILABLE:
            return "status.HTTP_503_SERVICE_UNAVAILABLE"
        case HTTPResponse.GATEWAY_TIMEOUT:
            return "status.HTTP_504_GATEWAY_TIMEOUT"
        case HTTPResponse.HTTP_VERSION_NOT_SUPPORTED:
            return "status.HTTP_505_HTTP_VERSION_NOT_SUPPORTED"
        case HTTPResponse.VARIANT_ALSO_NEGOTIATES:
            return "status.HTTP_506_VARIANT_ALSO_NEGOTIATES"
        case HTTPResponse.INSUFFICIENT_STORAGE:
            return "status.HTTP_507_INSUFFICIENT_STORAGE"
        case HTTPResponse.LOOP_DETECTED:
            return "status.HTTP_508_LOOP_DETECTED"
        case HTTPResponse.NOT_EXTENDED:
            return "status.HTTP_510_NOT_EXTENDED"
        case HTTPResponse.NETWORK_AUTHENTICATION_REQUIRED:
            return "status.HTTP_511_NETWORK_AUTHENTICATION_REQUIRED"
        case _:
            return ""


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
    return f"\n{INDENT}".join(properties)


# maybe return path to file instead of `None`
def create_serializer_file(definition: OpenAPIDefinition) -> None:
    schemas: list[str] = []
    for schema_name, schema in definition.created_schemas.items():
        schema_body = schema_to_drf(schema)
        schema_def = f"""
class {schema_name}Serializer(serializers.Serializer):
    {schema_body}
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

    export_file = Path(__file__).parent / "serializers.py"
    with export_file.open("w") as fp:
        for head in INITIAL_FILE_INPUTS:
            fp.write(head)
            fp.write("\n")

        for obj in schemas:
            fp.write(obj)

    isort.api.sort_file(export_file)
    black.format_file_in_place(export_file, mode=black.Mode(), fast=False, write_back=black.WriteBack.YES)


get_request_template = Template("""
    if request.method == "GET":
        $data
        $serializer
        return Response(serializer.data)
""")

"""
serializer = SnippetSerializer(data=request.data)
"""
post_request_template = Template("""
    if request.method == "POST":
        $serializer
        if serializer.is_valid():
            serializer.save()
            $response_success
        $response_error
""")

put_request_template = Template("""
    if request.method == "PUT":
        $serializer
        if serializer.is_valid():
            serializer.save()
            $response_success
        $response_error
""")

patch_request_template = Template("""
    if request.method == "PATCH":
        $serializer
        if serializer.is_valid():
            serializer.save()
            $response_success
        $response_error
""")

delete_request_template = Template("""
    if request.method == "DELETE":
        try:
            obj.delete()
        except IntegrityError:
            $response_error
        else:
            $response_success
""")


def create_request_and_response_objects(method: Method) -> str:
    func_txt = ""
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
                func_txt = get_request_template.substitute(data=example_data, serializer=schema_txt)
        case "post":
            request_schema = method.request_schema
            request_schema_txt = f"serializer = {request_schema.name}Serializer(data=request.data)"
            success_response_txt = f"return Response(serializer.data, status={to_drf_status_code(success_error_code)})"
            error_response_txt = f"return Response(serializer.errors, status={to_drf_status_code(fail_error_code)})"
            func_txt = post_request_template.substitute(
                serializer=request_schema_txt, response_success=success_response_txt, response_error=error_response_txt
            )
        case "put":
            request_schema = method.request_schema
            request_schema_txt = f"serializer = {request_schema.name}Serializer(data=request.data)"
            success_response_txt = f"return Response(serializer.data, status={to_drf_status_code(success_error_code)})"
            error_response_txt = f"return Response(serializer.errors, status={to_drf_status_code(fail_error_code)})"
            func_txt = put_request_template.substitute(
                serializer=request_schema_txt, response_success=success_response_txt, response_error=error_response_txt
            )
        case "patch":
            request_schema = method.request_schema
            request_schema_txt = f"serializer = {request_schema.name}Serializer(data=request.data)"
            success_response_txt = f"return Response(serializer.data, status={to_drf_status_code(success_error_code)})"
            error_response_txt = f"return Response(serializer.errors, status={to_drf_status_code(fail_error_code)})"
            func_txt = patch_request_template.substitute(
                serializer=request_schema_txt, response_success=success_response_txt, response_error=error_response_txt
            )
        case "delete":
            success_response_txt = f"return Response(serializer.data, status={to_drf_status_code(success_error_code)})"
            error_response_txt = f"return Response(serializer.errors, status={to_drf_status_code(fail_error_code)})"
            # func_txt = delete_request_template.substitute(
            #     response_success=success_response_txt, response_error=error_response_txt
            # )

    return func_txt


def create_view_func(path: ApiPath) -> str:
    function_name = convert_camel_case_to_snake_case(path.methods[0].operation_id)
    api_requests = [f'"{obj.request_type.upper()}"' for obj in path.methods]
    api_decorator_txt = f"@api_view([{', '.join(api_requests)}])"
    functions = []
    for method in path.methods:
        func_txt = create_request_and_response_objects(method)
        if len(functions) > 1:
            func_txt.replace("if", "else if", 1)
        functions.append(func_txt)
    function_txt = "\n".join(functions)
    if not function_txt.strip():
        function_txt = f"{INDENT}pass"

    query_params = "request"
    if params := path.get_query_params():
        query_params += ", "
        query_params += ", ".join(params)

    view_func_txt = f"""
{api_decorator_txt}
def {function_name}({query_params}):
{function_txt}
"""
    return view_func_txt


def create_view_file(open_API: OpenAPIDefinition) -> None:  # noqa: C0103
    views = []
    for path in open_API.paths:
        views.append(create_view_func(path))

    view_file = Path(__file__).parent / "views.py"
    with view_file.open("w") as fp:
        fp.write("\n".join(INITIAL_VIEW_FILE_INPUTS))
        fp.write("\n\n\n")
        fp.write("\n\n\n".join(views))

    isort.api.sort_file(view_file)
    black.format_file_in_place(view_file, mode=black.Mode(), fast=False, write_back=black.WriteBack.YES)
