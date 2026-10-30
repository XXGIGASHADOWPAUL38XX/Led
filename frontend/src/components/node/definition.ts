/** UI belongs here; Python supplies values, validation bounds, and port shapes. */
export type ControlKind = "port" | "slider" | "switch" | "select" | "axis" | "text" | "color" | "interval" | "array" | "shape" | "curve" | "reference" | "node-reference" | "sequence" | "managed";
export type FieldDefinition = {
  name: string; control: ControlKind; label?: string; unit?: string;
  scale?: "linear" | "logarithmic"; min?: number; max?: number;
  item?: "reference" | "node" | "token"; nodeTypes?: string[];
  rebuild?: boolean; bounds?: { from: string; min: number; max: number };
  matchInput?: string;
  hidden?: boolean; portsPrefix?: string;
  channels?: string[];
};
export type ViewDefinition = { kind: "bars" | "history" | "color" | "lights" | "trigger" | "meter" | "playlist"; data?: string; colors?: string; label?: string; series?: string[]; open?: boolean; unit?: string; xScale?: "linear" | "logarithmic"; xMinField?: string; xMaxField?: string };
export type NodeDefinition = {
  type: string; title: string; description: string; category: string;
  fields: FieldDefinition[]; views: ViewDefinition[]; actions?: ("start" | "stop")[];
};
