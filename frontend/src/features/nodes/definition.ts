import type { components } from "@/api/schema";

/** UI belongs to each Python node class (`ui`); these types are generated from backend/api/schemas.py. */
type Schemas = components["schemas"];
export type ControlKind = Schemas["FieldUi"]["control"];
export type FieldDefinition = Schemas["FieldUi"];
export type ViewDefinition = Schemas["ViewUi"];
export type NodeDefinition = Schemas["CatalogNode"];
