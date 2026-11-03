"""Print the API contract as an OpenAPI document: python -m backend.api.openapi > frontend/src/api/openapi.json"""
import json

from pydantic.json_schema import models_json_schema

from .schemas import COMMANDS, EVENTS


def document():
    models = [(model, "serialization") for model in EVENTS.values()] + [(model, "validation") for model in COMMANDS.values()]
    _, schema = models_json_schema(list(dict.fromkeys(models)), ref_template="#/components/schemas/{model}")
    return {"openapi": "3.1.0", "info": {"title": "LED backend", "version": "1"}, "paths": {},
            "components": {"schemas": schema["$defs"]}}


if __name__ == "__main__":
    print(json.dumps(document(), indent=2, sort_keys=True))
