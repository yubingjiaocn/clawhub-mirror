import { describe, it, expect, vi, beforeEach } from "vitest";

// We need to mock fetch before importing api module
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

// Mock import.meta.env
vi.stubGlobal("location", { origin: "http://localhost:3000" });

// Now import the functions under test
import {
  listSkills,
  getSkill,
  getVersions,
  searchSkills,
  downloadSkill,
  publishSkill,
  login,
  register,
  logout,
  whoami,
  listApiKeys,
  createApiKey,
  revokeApiKey,
  listUsers,
  createUser,
  updateUserRole,
  deleteUser,
  listPolicies,
  createPolicy,
  updatePolicy,
  deletePolicy,
  getProxySettings,
  updateProxySettings,
} from "./api";

function jsonResponse(data: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "Error",
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  });
}

function errorResponse(status: number, detail: string) {
  return Promise.resolve({
    ok: false,
    status,
    statusText: "Error",
    json: () => Promise.resolve({ detail }),
    text: () => Promise.resolve(JSON.stringify({ detail })),
  });
}

beforeEach(() => {
  mockFetch.mockReset();
  localStorage.clear();
});

describe("api helpers", () => {
  it("includes auth header when token is stored", async () => {
    localStorage.setItem("clawhub-token", "test-token");
    mockFetch.mockReturnValue(jsonResponse({ items: [], nextCursor: null }));

    await listSkills();

    const [, opts] = mockFetch.mock.calls[0];
    expect(opts.headers["Authorization"]).toBe("Bearer test-token");
  });

  it("omits auth header when no token", async () => {
    mockFetch.mockReturnValue(jsonResponse({ items: [], nextCursor: null }));

    await listSkills();

    const [, opts] = mockFetch.mock.calls[0];
    expect(opts.headers["Authorization"]).toBeUndefined();
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockReturnValue(errorResponse(401, "Unauthorized"));

    await expect(listSkills()).rejects.toThrow();
  });
});

describe("skill endpoints", () => {
  beforeEach(() => localStorage.setItem("clawhub-token", "tok"));

  it("listSkills sends correct request", async () => {
    mockFetch.mockReturnValue(jsonResponse({ items: [], nextCursor: null }));
    await listSkills({ limit: 10, cursor: "abc" });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/v1/skills");
    expect(url).toContain("limit=10");
    expect(url).toContain("cursor=abc");
  });

  it("getSkill sends correct path", async () => {
    mockFetch.mockReturnValue(jsonResponse({ skill: {}, latestVersion: null, owner: {} }));
    await getSkill("my-skill");
    expect(mockFetch.mock.calls[0][0]).toContain("/api/v1/skills/my-skill");
  });

  it("getVersions sends correct path", async () => {
    mockFetch.mockReturnValue(jsonResponse({ versions: [] }));
    await getVersions("my-skill");
    expect(mockFetch.mock.calls[0][0]).toContain("/api/v1/skills/my-skill/versions");
  });

  it("searchSkills encodes query", async () => {
    mockFetch.mockReturnValue(jsonResponse({ results: [] }));
    await searchSkills("hello world");
    expect(mockFetch.mock.calls[0][0]).toContain("q=hello%20world");
  });

  it("downloadSkill returns URL with params", () => {
    localStorage.setItem("clawhub-token", "tok123");
    const url = downloadSkill("my-skill", "1.0.0");
    expect(url).toContain("slug=my-skill");
    expect(url).toContain("version=1.0.0");
    expect(url).toContain("token=tok123");
  });

  it("publishSkill sends FormData without Content-Type", async () => {
    mockFetch.mockReturnValue(jsonResponse({ slug: "s", version: "1.0.0", message: "ok" }));
    const fd = new FormData();
    fd.append("slug", "s");
    await publishSkill(fd);

    const [, opts] = mockFetch.mock.calls[0];
    expect(opts.method).toBe("POST");
    expect(opts.body).toBe(fd);
    // Should not set Content-Type for FormData (browser sets boundary)
    expect(opts.headers["Content-Type"]).toBeUndefined();
  });
});

describe("auth endpoints", () => {
  it("login sends POST with credentials", async () => {
    mockFetch.mockReturnValue(jsonResponse({ token: "t", username: "u", role: "reader" }));
    const resp = await login("user1", "pass1");

    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/v1/auth/login");
    expect(opts.method).toBe("POST");
    expect(JSON.parse(opts.body)).toEqual({ username: "user1", password: "pass1" });
    expect(resp.token).toBe("t");
  });

  it("register sends POST with credentials", async () => {
    mockFetch.mockReturnValue(jsonResponse({ token: "t", username: "u", role: "reader" }));
    const resp = await register("newuser", "pass");

    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/v1/auth/register");
    expect(opts.method).toBe("POST");
    expect(resp.username).toBe("u");
  });

  it("logout sends POST with token", async () => {
    localStorage.setItem("clawhub-token", "session-tok");
    mockFetch.mockReturnValue(jsonResponse({}));
    await logout();

    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/v1/auth/logout");
    expect(opts.headers["Authorization"]).toBe("Bearer session-tok");
  });

  it("logout does nothing without token", async () => {
    await logout();
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("whoami sends GET", async () => {
    localStorage.setItem("clawhub-token", "tok");
    mockFetch.mockReturnValue(jsonResponse({ username: "u", role: "admin", handle: "u" }));
    const resp = await whoami();
    expect(resp.username).toBe("u");
  });
});

describe("API key endpoints", () => {
  beforeEach(() => localStorage.setItem("clawhub-token", "tok"));

  it("listApiKeys sends GET", async () => {
    mockFetch.mockReturnValue(jsonResponse([]));
    await listApiKeys();
    expect(mockFetch.mock.calls[0][0]).toContain("/api/v1/auth/keys");
  });

  it("createApiKey sends POST with label", async () => {
    mockFetch.mockReturnValue(jsonResponse({ keyId: "k", label: "test", token: "t", createdAt: 0 }));
    await createApiKey("my-label");
    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.label).toBe("my-label");
  });

  it("revokeApiKey sends DELETE", async () => {
    mockFetch.mockReturnValue(jsonResponse({ detail: "revoked" }));
    await revokeApiKey("key123");
    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/v1/auth/keys/key123");
    expect(opts.method).toBe("DELETE");
  });
});

describe("admin endpoints", () => {
  beforeEach(() => localStorage.setItem("clawhub-token", "admin-tok"));

  it("listUsers sends GET", async () => {
    mockFetch.mockReturnValue(jsonResponse([]));
    await listUsers();
    expect(mockFetch.mock.calls[0][0]).toContain("/api/v1/admin/users");
  });

  it("createUser sends POST", async () => {
    mockFetch.mockReturnValue(jsonResponse({ user: {}, apiToken: "t" }));
    await createUser({ username: "u", password: "p", role: "reader" });
    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.username).toBe("u");
    expect(body.role).toBe("reader");
  });

  it("updateUserRole sends PATCH", async () => {
    mockFetch.mockReturnValue(jsonResponse({ username: "u", role: "publisher", isActive: true, createdAt: 0 }));
    await updateUserRole("u", "publisher");
    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/v1/admin/users/u");
    expect(opts.method).toBe("PATCH");
    expect(JSON.parse(opts.body).role).toBe("publisher");
  });

  it("deleteUser sends DELETE", async () => {
    mockFetch.mockReturnValue(jsonResponse({ detail: "deactivated" }));
    await deleteUser("u");
    expect(mockFetch.mock.calls[0][1].method).toBe("DELETE");
  });

  it("updatePolicy sends PATCH", async () => {
    mockFetch.mockReturnValue(jsonResponse({ id: "s", slug: "s", policyType: "deny" }));
    await updatePolicy("my-slug", { policy_type: "deny", notes: "blocked" });
    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/v1/admin/policies/my-slug");
    expect(opts.method).toBe("PATCH");
    const body = JSON.parse(opts.body);
    expect(body.policy_type).toBe("deny");
    expect(body.notes).toBe("blocked");
  });

  it("getProxySettings sends GET", async () => {
    mockFetch.mockReturnValue(jsonResponse({ enabled: false, upstreamUrl: "https://clawhub.ai" }));
    const resp = await getProxySettings();
    expect(resp.enabled).toBe(false);
  });

  it("updateProxySettings sends PUT", async () => {
    mockFetch.mockReturnValue(jsonResponse({ enabled: true, upstreamUrl: "https://clawhub.ai" }));
    await updateProxySettings({ enabled: true });
    const [, opts] = mockFetch.mock.calls[0];
    expect(opts.method).toBe("PUT");
  });
});
