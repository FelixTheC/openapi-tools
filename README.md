# openapi-tools

Generate starter Django REST Framework (DRF) serializers and views from an OpenAPI v3 file.

## Who is this for?
- For people who have an OpenAPI file and want a quick starting point for a DRF project.
- You’ll get basic serializers and view functions you can customize — no OpenAPI knowledge required.

## What you’ll get
- serializers.py: one DRF Serializer per schema in your OpenAPI file
- views.py: simple view functions for the documented API endpoints
- Both files are formatted automatically

## Requirements
- Python 3.13 or newer

## Install
Option A: Using uv (recommended)
- Install uv if you don’t have it yet: https://docs.astral.sh/uv/
- In this project folder run: uv sync

## Option B: Using pip
- Create/activate a virtual environment
- In this project folder run: pip install -e .

## Quick start
1) Make sure you’re in the project folder.
2) Use the provided example OpenAPI file to try it out:
- python -m openapi_reader.reader tests/openapi.yaml
3) That’s it! The generator will create or overwrite these files:
- openapi_reader/serializers.py
- openapi_reader/views.py

## Choose a different output folder (optional)
- If you don’t want to overwrite the files inside openapi_reader/, choose a folder:
- python -m openapi_reader.reader tests/openapi.yaml --export-folder out
- The generated files will be written to the out/ folder.

## What the generated code looks like
### Serializer example (Pet)
```python
class PetSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    category = CategorySerializer()
    photourls = serializers.CharField()
    tags = TagSerializer(many=True)
    status = serializers.CharField()
```

### View example (find pets by status)
```python
@api_view(["GET"])  
def find_pets_by_status(request):
    serializer = FindPetsByStatusSerializer(data=request.query_params)
    if not serializer.is_valid():
        return Response(serializer.errors, status=drf_status.HTTP_400_BAD_REQUEST)
    data = {}
    serializer = PetSerializer(data)
    return Response(serializer.data)
```

### Url dispatcher example (find pets by status)
```python
urlatterns = [
    ...
    path("/pet/<int:pet_id>/", get_pet_by_id),
    ...
]
```

### More examples
- See the examples/ folder for more examples.

## Next steps: use it in your project
- Move or copy the generated files into your Django app, for example into myapp/serializers.py and myapp/views.py
- Wire the views to URLs (urls.py)
- Replace placeholder logic in the views with your real code (database queries, permissions, etc.)
- Adjust field types in serializers if needed

## Command options (simple)
- --export-folder PATH  Write the generated files into PATH instead of openapi_reader/
- --framework drf       Only "drf" is supported right now (no action needed)

## Troubleshooting
- Command not found / Python mismatch
  - Make sure you’re using Python 3.13+: python --version
  - If you’re in a virtual environment, activate it first
- "OpenAPI schema file not found"
  - Check the path you passed to the command actually exists
- Import errors when running the command
  - Install dependencies with uv sync or pip install -e .

## FAQ
- Will this write anywhere else?  
  No. It only writes the generated serializers.py and views.py to the chosen folder.
- Is the code production-ready?  
  It’s a starting point. You’ll need to fill in the actual view logic and adjust serializers to match your models.
- Can I re-run the generator?  
  Yes. Running again will overwrite the previously generated files in the target location.

## Need a quick demo again?
- python -m openapi_reader.reader tests/openapi.yaml
- or write to another folder: python -m openapi_reader.reader tests/openapi.yaml --export-folder out

Enjoy building with DRF!