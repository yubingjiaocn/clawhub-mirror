const API_BASE = import.meta.env.VITE_API_URL || window.location.origin;

function getToken(): string | null {
  return localStorage.getItem("clawhub-token");
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `${res.status} ${res.statusText}`);
  }

  return res.json();
}

// Helper functions
function get<T>(path: string) { return request<T>("GET", path); }
function post<T>(path: string, body?: unknown) { return request<T>("POST", path, body); }
function del<T>(path: string) { return request<T>("DELETE", path); }

// Types
export type Skill = {
  slug: string;
  displayName: string;
  summary: string;
  tags: string[];
  owner: string;
  downloads: number;
  stars: number;
  latestVersion: string;
  createdAt: string;
  updatedAt: string;
};

export type SkillVersion = {
  version: string;
  changelog: string;
  createdAt: string;
  files: string[];
};

export type SkillDetail = Skill & {
  readme: string;
  versions: SkillVersion[];
};

export type User = {
  id: string;
  username: string;
  role: string;
  createdAt: string;
};

export type Policy = {
  id: string;
  kind: string;
  value: string;
  createdAt: string;
};

// Skill API functions
export function listSkills(params?: { sort?: string; order?: string; cursor?: string; limit?: number }) {
  const query = new URLSearchParams();
  if (params?.sort) query.set("sort", params.sort);
  if (params?.order) query.set("order", params.order);
  if (params?.cursor) query.set("cursor", params.cursor);
  if (params?.limit) query.set("limit", params.limit.toString());

  const path = `/api/skills${query.toString() ? `?${query.toString()}` : ""}`;
  return get<{ skills: Skill[]; nextCursor?: string }>(path);
}

export function getSkill(slug: string) {
  return get<SkillDetail>(`/api/skills/${slug}`);
}

export function getVersions(slug: string) {
  return get<{ versions: SkillVersion[] }>(`/api/skills/${slug}/versions`);
}

export function searchSkills(q: string) {
  return get<{ skills: Skill[] }>(`/api/skills?q=${encodeURIComponent(q)}`);
}

export function resolveSkill(slug: string, version?: string) {
  const path = `/api/skills/${slug}/resolve${version ? `?version=${encodeURIComponent(version)}` : ""}`;
  return get<{ url: string; version: string }>(path);
}

export function downloadSkill(slug: string, version?: string): string {
  return `${API_BASE}/api/skills/${slug}/download${version ? `?version=${encodeURIComponent(version)}` : ""}`;
}

export async function publishSkill(formData: FormData) {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/api/skills`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `${res.status} ${res.statusText}`);
  }

  return res.json();
}

// Auth API functions
export function whoami() {
  return get<User>("/api/auth/whoami");
}

export async function login(token: string) {
  localStorage.setItem("clawhub-token", token);
  return whoami();
}

export function logout() {
  localStorage.removeItem("clawhub-token");
}

// Admin API functions
export function listUsers() {
  return get<{ users: User[] }>("/api/admin/users");
}

export function createUser(data: { username: string; role?: string }) {
  return post<User>("/api/admin/users", data);
}

export function deleteUser(id: string) {
  return del<{ success: boolean }>(`/api/admin/users/${id}`);
}

export function listPolicies() {
  return get<{ policies: Policy[] }>("/api/admin/policies");
}

export function createPolicy(data: { kind: string; value: string }) {
  return post<Policy>("/api/admin/policies", data);
}

export function deletePolicy(id: string) {
  return del<{ success: boolean }>(`/api/admin/policies/${id}`);
}
