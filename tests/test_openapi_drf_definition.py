from openapi_reader.schema import OpenAPIDefinition


def test_create_drf_serializers(openapi_yaml):
    definition = OpenAPIDefinition(openapi_yaml)
    definition.parse()
    from openapi_reader.drf import create_serializer_file

    create_serializer_file(definition)


def test_create_view_funcs(openapi_yaml):
    definition = OpenAPIDefinition(openapi_yaml)
    definition.parse()

    from openapi_reader.drf import create_view_file

    create_view_file(definition)
    # create_view_file(definition, use_tempdir=True)


def test_create_dispatcher_file(openapi_yaml):
    definition = OpenAPIDefinition(openapi_yaml)
    definition.parse()

    from openapi_reader.drf import create_urls_file

    create_urls_file(definition)
