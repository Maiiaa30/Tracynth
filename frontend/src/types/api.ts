export type ApiRecord = Record<string, unknown>;

export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ApiErrorBody {
  error?: {
    code?: string;
    message?: string;
    fields?: Record<string, string[] | string>;
  };
  detail?: string;
}

export interface User {
  id?: string;
  username: string;
  email?: string;
}

export interface SessionResponse {
  authenticated: boolean;
  user?: User;
}

export interface Scan extends ApiRecord {
  id: string;
  status?: string;
  state?: string;
  progress?: number;
  created_at?: string;
  updated_at?: string;
  target?: unknown;
  modules?: unknown;
}

export interface GraphEntity extends ApiRecord {
  id: string;
  display_value?: string;
  value?: string;
  entity_type?: string;
  type?: string;
}

export interface GraphRelationship extends ApiRecord {
  id: string;
  source?: string | { id?: string };
  target?: string | { id?: string };
  relationship_type?: string;
  type?: string;
  confidence?: number;
}
