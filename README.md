# py-openapi-tools

Generate starter code for your API from an OpenAPI v3 file.

Supported frameworks:
- Django REST Framework (DRF)
- FastAPI

## Who is this for?
- You have an OpenAPI file and want a quick starting point for a Python web project.
- You’ll get basic serializers/models and view functions you can customize — no OpenAPI internals required.

## What gets generated
- DRF
  - serializers.py: one DRF Serializer per schema in your OpenAPI file
  - views.py: API views with request/response serialization and status codes
  - urls.py: url patterns wiring view functions/classes
- FastAPI
  - serializers.py: Pydantic models for request/response bodies and components
  - views.py: FastAPI route handlers using the generated models

All files are auto-formatted (isort + black).

## Requirements
- Python 3.13 or newer

## Install
Option A: Using uv (recommended)
- Install uv if you don’t have it yet: https://docs.astral.sh/uv/
- In this project folder run: uv sync

Option B: Using pip
- Create/activate a virtual environment
- In this project folder run: pip install -e .

After installation, the CLI `py-openapi-tools` is available.

## Quick start
Try with the provided example spec:

- DRF
  - `py-openapi-tools tests/openapi.yaml --framework drf --export-folder out`
  - Generated: out/serializers.py, out/views.py, out/urls.py

- FastAPI
  - `py-openapi-tools tests/openapi.yaml --framework fastapi --export-folder out`
  - Generated: out/serializers.py, out/views.py

You can also run via Python module:
- `python -m py_openapi_tools.reader tests/openapi.yaml --framework drf --export-folder out`

## Using the generated code
- DRF
  - Move or copy generated files into your Django app, e.g. myapp/serializers.py, myapp/views.py, myapp/urls.py
  - Include urls in your project’s urlconf
  - Replace placeholder logic in the views with real code (queries, permissions, etc.)
  - Adjust serializer field types as needed
- FastAPI
  - Import generated models and routes into your FastAPI app
  - Fill in the route implementations

## Command options
- --export-folder PATH  Write generated files into PATH (defaults to a temporary file preview when omitted)
- --framework [drf|fastapi]  Select target framework (default: drf)

## Examples
- See the tests/ folder for example OpenAPI files:
  - tests/openapi.yaml
  - tests/openapi_examples.yaml
- Also check examples/ for simple integration sketches.

## Troubleshooting
- Command not found / Python mismatch
  - Ensure Python 3.13+: python --version
  - Activate your virtual environment
- "OpenAPI schema file not found"
  - Verify the path to your OpenAPI file
- Import errors or formatting issues
  - Install dependencies with uv sync or pip install -e .

## FAQ
- Where are files written?
  - Only to the chosen export folder (or a temporary preview when not specified).
- Is the code production-ready?
  - It’s a starting point. You should adapt view logic, security, and data access for your app.
- Can I re-run the generator?
  - Yes. Running again will overwrite previously generated files in the target location.

Happy building with DRF and FastAPI!