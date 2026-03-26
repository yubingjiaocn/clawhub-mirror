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
function patch<T>(path: string, body?: unknown) { return request<T>("PATCH", path, body); }
function del<T>(path: string) { return request<T>("DELETE", path); }

// --- Types matching backend Pydantic schemas ---

export type VersionInfo = {
  version: string;
  createdAt: number;
  changelog: string | null;
};

export type SkillStats = {
  downloads: number;
  stars: number;
};

export type OwnerInfo = {
  handle: string;
  displayName: string;
};

export type SkillListItem = {
  slug: string;
  displayName: string;
  summary: string | null;
  tags: string[];
  stats: SkillStats;
  createdAt: number;
  updatedAt: number;
  latestVersion: VersionInfo | null;
};

export type SkillListResponse = {
  items: SkillListItem[];
  nextCursor: string | null;
};

export type SkillDetailResponse = {
  skill: SkillListItem;
  latestVersion: VersionInfo | null;
  owner: OwnerInfo;
};

export type SkillVersionsResponse = {
  versions: VersionInfo[];
};

export type SearchResultItem = {
  slug: string;
  displayName: string;
  summary: string | null;
  version: string | null;
  score: number;
  updatedAt: number;
};

export type SearchResponse = {
  results: SearchResultItem[];
};

export type ResolveResponse = {
  match: { version: string } | null;
  latestVersion: VersionInfo | null;
};

export type PublishResponse = {
  slug: string;
  version: string;
  message: string;
};

export type WhoamiResponse = {
  username: string;
  role: string;
  handle: string;
};

export type UserSchema = {
  username: string;
  role: string;
  isActive: boolean;
  createdAt: number;
};

export type UserCreateResponse = {
  user: UserSchema;
  apiToken: string;
};

export type AdmissionPolicy = {
  id: string;
  slug: string;
  allowedVersions: string | null;
  policyType: string;
  approvedBy: string | null;
  approvedAt: number | null;
  notes: string | null;
  createdAt: number;
};

export type PendingRequest = {
  id: string;
  slug: string;
  requestedBy: string | null;
  requestedAt: number | null;
  reason: string | null;
  status: string;
};

// --- Skill API functions ---

export function listSkills(params?: { cursor?: string; limit?: number }) {
  const query = new URLSearchParams();
  if (params?.cursor) query.set("cursor", params.cursor);
  if (params?.limit) query.set("limit", params.limit.toString());

  const qs = query.toString();
  const path = `/api/v1/skills${qs ? `?${qs}` : ""}`;
  return get<SkillListResponse>(path);
}

export function getSkill(slug: string) {
  return get<SkillDetailResponse>(`/api/v1/skills/${slug}`);
}

export function getVersions(slug: string) {
  return get<SkillVersionsResponse>(`/api/v1/skills/${slug}/versions`);
}

export function searchSkills(q: string) {
  return get<SearchResponse>(`/api/v1/search?q=${encodeURIComponent(q)}`);
}

export function resolveSkill(slug: string, hash?: string) {
  const query = new URLSearchParams({ slug });
  if (hash) query.set("hash", hash);
  return get<ResolveResponse>(`/api/v1/resolve?${query.toString()}`);
}

export function downloadSkill(slug: string, version: string): string {
  const token = getToken();
  const query = new URLSearchParams({ slug, version });
  if (token) query.set("token", token);
  return `${API_BASE}/api/v1/download?${query.toString()}`;
}

export async function publishSkill(formData: FormData) {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/api/v1/skills`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `${res.status} ${res.statusText}`);
  }

  return res.json() as Promise<PublishResponse>;
}

// --- Auth API functions ---

export function whoami() {
  return get<WhoamiResponse>("/api/v1/whoami");
}

export async function login(token: string) {
  localStorage.setItem("clawhub-token", token);
  return whoami();
}

export function logout() {
  localStorage.removeItem("clawhub-token");
}

// --- Admin API functions ---

export function listUsers() {
  return get<UserSchema[]>("/api/v1/admin/users");
}

export function createUser(data: { username: string; password: string; role?: string }) {
  return post<UserCreateResponse>("/api/v1/admin/users", data);
}

export function deleteUser(username: string) {
  return del<{ detail: string }>(`/api/v1/admin/users/${username}`);
}

export function listPolicies() {
  return get<{ policies: AdmissionPolicy[] }>("/api/v1/admin/policies");
}

export function createPolicy(data: { slug: string; policy_type?: string; allowed_versions?: string; notes?: string }) {
  return post<AdmissionPolicy>("/api/v1/admin/policies", data);
}

export function updatePolicy(slug: string, data: { policy_type?: string; allowed_versions?: string; notes?: string }) {
  return patch<AdmissionPolicy>(`/api/v1/admin/policies/${slug}`, data);
}

export function deletePolicy(slug: string) {
  return del<{ detail: string }>(`/api/v1/admin/policies/${slug}`);
}

export function listPendingRequests() {
  return get<{ requests: PendingRequest[] }>("/api/v1/admin/policies/pending");
}

export function approvePending(requestId: string) {
  return post<AdmissionPolicy>(`/api/v1/admin/policies/pending/${requestId}/approve`);
}

export function denyPending(requestId: string) {
  return post<{ detail: string }>(`/api/v1/admin/policies/pending/${requestId}/deny`);
}
