import pprint
from pathlib import Path
import yaml


def read_openapi_schema(file: Path) -> dict | None:
    if not file.exists():
        return None

    with file.open() as fp:
        return yaml.safe_load(fp)


if __name__ == "__main__":
    pprint.pprint(read_openapi_schema(Path("../tests/openapi.yaml")))
