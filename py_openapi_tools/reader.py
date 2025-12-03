from pathlib import Path
import yaml
import click

from py_openapi_tools.schema import OpenAPIDefinition


def read_openapi_schema(file: Path) -> dict | None:
    if not file.exists():
        return None

    with file.open() as fp:
        return yaml.safe_load(fp)


@click.command()
@click.argument("openapifile", type=click.Path(exists=True))
@click.option("--export-folder", type=click.Path(), default=None)
@click.option(
    "--framework",
    type=click.Choice(["drf", "fastapi"]),
    default="drf",
)
def main(openapifile: Path, export_folder: Path | None = None, framework: str = "drf"):
    openapi_yaml = read_openapi_schema(openapifile)
    if not openapi_yaml:
        click.echo("OpenAPI schema file not found")
        return

    definition = OpenAPIDefinition(openapi_yaml)
    definition.parse()
    use_tempdir = export_folder is None

    if framework == "drf":
        from py_openapi_tools.drf import create_view_file, create_serializer_file, create_urls_file

        create_serializer_file(definition, export_folder=export_folder, use_tempdir=use_tempdir)
        create_view_file(definition, export_folder=export_folder, use_tempdir=use_tempdir)
        create_urls_file(definition, export_folder=export_folder, use_tempdir=use_tempdir)

    if framework == "fastapi":
        from py_openapi_tools.fastapi import create_view_file, create_serializer_file

        create_serializer_file(
            definition,
            export_folder=export_folder,
            use_tempdir=use_tempdir,
        )
        create_view_file(definition, export_folder=export_folder, use_tempdir=use_tempdir)
