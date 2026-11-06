/** UI belongs here; Python supplies values, validation bounds, and port shapes. */
export type ControlKind = "port" | "slider" | "switch" | "select" | "axis" | "text" | "color" | "interval" | "array" | "shape" | "curve" | "reference" | "node-reference" | "sequence" | "expression" | "clustering" | "blend" | "managed";
export type FieldDefinition = {
  name: string; control: ControlKind; label?: string; unit?: string;
  scale?: "linear" | "logarithmic"; min?: number; max?: number; step?: number;
  item?: "reference" | "node" | "token"; nodeTypes?: string[];
  rebuild?: boolean; bounds?: { from: string; min: number; max: number };
  matchInput?: string;
  ordered?: boolean;
  permutation?: boolean;
  hidden?: boolean; portsPrefix?: string;
  channels?: string[];
  addPort?: string;
};
export type ViewDefinition = {
  data?: string; colors?: string; status?: string; label?: string; series?: string[]; open?: boolean;
  unit?: string; xScale?: "linear" | "logarithmic"; xMinField?: string; xMaxField?: string;
} & ({ kind: "scatter"; data: string; status: string }
  | { kind: "bars" | "history" | "color" | "lights" | "trigger" | "meter" | "playlist" | "clustering" | "angle" });
export type NodeDefinition = {
  type: string; title: string; description: string; category: string;
  fields: FieldDefinition[]; views: ViewDefinition[]; actions?: ("start" | "stop" | "recalibrate")[];
};
