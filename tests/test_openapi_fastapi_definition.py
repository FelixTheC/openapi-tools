from openapi_reader.schema import OpenAPIDefinition


def test_openapi_fastapi_definition(openapi_yaml):
    definition = OpenAPIDefinition(openapi_yaml)
    definition.parse()

    from openapi_reader.fastapi import create_serializer_file

    create_serializer_file(definition)


def test_openapi_fastapi_definition_view(openapi_yaml):
    definition = OpenAPIDefinition(openapi_yaml)
    definition.parse()

    from openapi_reader.fastapi import create_view_file

    create_view_file(definition)
