from pathlib import Path

import pytest

from openapi_reader.reader import read_openapi_schema


@pytest.fixture(autouse=True, scope="session")
def openapi_yaml():
    data = read_openapi_schema(Path(__file__).parent / "openapi.yaml")
    yield data


@pytest.fixture(autouse=True, scope="session")
def openapi_example_yaml():
    data = read_openapi_schema(Path(__file__).parent / "openapi_examples.yaml")
    yield data
