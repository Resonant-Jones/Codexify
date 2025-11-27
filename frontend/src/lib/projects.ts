// Normalizes any /projects response shape into [{ id, name, icon, ... }]
export function normalizeProjectsResponse(res: any) {
  const payload = res?.data ?? res;
  const list = Array.isArray(payload)
    ? payload
    : Array.isArray(payload?.projects)
      ? payload.projects
      : [];

  return list.map((p: any) => ({
    id: String(p.id ?? p.project_id),
    name: p.name ?? p.project_name ?? "Untitled",
    icon: p.icon ?? "📁",
    description: p.description ?? "",
    created_at: p.created_at,
    updated_at: p.updated_at,
  }));
}

// Pulls the new project's id from POST /projects result
export function extractProjectId(res: any): string | null {
  const d = res?.data ?? res;
  const id = d?.id ?? d?.project_id;
  return id != null ? String(id) : null;
}
