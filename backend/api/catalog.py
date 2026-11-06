"""The editor's node catalog: every class's `ui`, validated once at startup and served by version."""
from hashlib import sha256

from pydantic import TypeAdapter

from .schemas import CatalogNode

CATALOG = TypeAdapter(list[CatalogNode])


class Catalog:
    def __init__(self, classes):
        nodes = [CatalogNode(type=name, **cls.ui) for name, cls in classes.items()]
        self.body = CATALOG.dump_json(nodes, exclude_none=True, by_alias=True)
        self.etag = f'"{sha256(self.body).hexdigest()[:16]}"'
