export type Row = Record<string, string | number | boolean | null>;

export interface ToolCall {
  tool: string;
  arguments: Record<string, unknown>;
  rows: Row[];
  cached: boolean;
  error: string | null;
}

export interface AskResponse {
  session_id: string;
  answer: string;
  tool_calls: ToolCall[];
}
