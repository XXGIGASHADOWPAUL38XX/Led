"""Print the API contract as OpenAPI: python -m backend.api.openapi (npm run api:generate in frontend/)."""
import json

from fastapi import FastAPI
from pydantic.json_schema import models_json_schema

from .schemas import COMMANDS, EVENTS


def contract():
    """WebSocket commands and events: no HTTP route references them, so FastAPI alone would leave them out."""
    models = [(model, "serialization") for model in EVENTS.values()] + [(model, "validation") for model in COMMANDS.values()]
    _, schema = models_json_schema(list(dict.fromkeys(models)), ref_template="#/components/schemas/{model}")
    return schema["$defs"]


def document(app):
    """The app's OpenAPI document (HTTP routes) extended with the WebSocket contract; cached by FastAPI."""
    if app.openapi_schema is None:
        FastAPI.openapi(app).setdefault("components", {}).setdefault("schemas", {}).update(contract())
    return app.openapi_schema


if __name__ == "__main__":
    from .server import create_app
    print(json.dumps(document(create_app(None)), indent=2, sort_keys=True))
