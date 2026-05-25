export interface HealthResponse {
  status: string;
  service: string;
}

// Sprint 2+: expand as AI pipeline schemas are defined.
export interface Session {
  id: string;
  title: string;
  status: "pending" | "processing" | "done" | "error";
  created_at: string;
}
