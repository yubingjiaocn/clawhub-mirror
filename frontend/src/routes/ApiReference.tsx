import { useState } from "react";

type Section = "auth" | "skills" | "keys" | "admin" | "discovery";

function Endpoint({ method, path, auth, desc }: {
  method: string; path: string; auth: string; desc: string;
}) {
  const methodColor: Record<string, string> = {
    GET: "#22c55e", POST: "#3b82f6", DELETE: "#ef4444", PATCH: "#f59e0b",
  };
  return (
    <div style={{
      display: "flex", gap: "8px", alignItems: "baseline",
      padding: "6px 0", borderBottom: "1px solid var(--line)",
    }}>
      <span style={{
        background: methodColor[method] || "#888",
        color: "#fff", fontSize: "0.7rem", fontWeight: 700,
        padding: "2px 6px", borderRadius: "4px", minWidth: "52px",
        textAlign: "center", flexShrink: 0,
      }}>{method}</span>
      <code style={{ fontSize: "0.85rem", flex: 1 }}>{path}</code>
      <span style={{ fontSize: "0.75rem", color: "var(--muted)", flexShrink: 0 }}>{auth}</span>
    </div>
  );
}

function Block({ title, children, lang = "json" }: { title: string; children: string; lang?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div style={{
      background: "var(--surface)", border: "1px solid var(--line)",
      borderRadius: "8px", overflow: "hidden", marginBottom: "12px",
    }}>
      <div style={{
        padding: "8px 12px", borderBottom: "1px solid var(--line)",
        display: "flex", justifyContent: "space-between", alignItems: "center",
      }}>
        <strong style={{ fontSize: "0.8rem" }}>{title}</strong>
        <button type="button" style={{
          background: "none", border: "none", color: "var(--muted)",
          cursor: "pointer", fontSize: "0.75rem",
        }} onClick={() => { navigator.clipboard.writeText(children.trim()); setCopied(true); setTimeout(() => setCopied(false), 1500); }}>
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
      <pre style={{ padding: "12px", margin: 0, fontSize: "0.8rem", overflowX: "auto", lineHeight: 1.5 }}>
        <code>{children.trim()}</code>
      </pre>
    </div>
  );
}

function SectionBlock({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} style={{ marginBottom: "48px" }}>
      <h2 style={{ fontSize: "1.25rem", marginBottom: "16px", paddingBottom: "8px", borderBottom: "2px solid var(--line)" }}>{title}</h2>
      {children}
    </section>
  );
}

function EndpointDetail({ method, path, auth, desc, children }: {
  method: string; path: string; auth: string; desc: string; children: React.ReactNode;
}) {
  const methodColor: Record<string, string> = {
    GET: "#22c55e", POST: "#3b82f6", DELETE: "#ef4444", PATCH: "#f59e0b",
  };
  return (
    <div style={{ marginBottom: "32px" }}>
      <div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "4px" }}>
        <span style={{
          background: methodColor[method] || "#888", color: "#fff",
          fontSize: "0.75rem", fontWeight: 700, padding: "2px 8px", borderRadius: "4px",
        }}>{method}</span>
        <code style={{ fontSize: "1rem", fontWeight: 600 }}>{path}</code>
      </div>
      <p style={{ margin: "4px 0 12px", color: "var(--muted)", fontSize: "0.9rem" }}>
        {desc} <span style={{ fontSize: "0.8rem" }}>({auth})</span>
      </p>
      {children}
    </div>
  );
}

export function ApiReference() {
  const base = window.location.origin;
  const [activeSection, setActiveSection] = useState<Section>("auth");

  const nav: Array<{ id: Section; label: string }> = [
    { id: "auth", label: "Auth" },
    { id: "skills", label: "Skills" },
    { id: "keys", label: "API Keys" },
    { id: "admin", label: "Admin" },
    { id: "discovery", label: "Discovery" },
  ];

  return (
    <main className="section" style={{ maxWidth: "820px", margin: "0 auto", padding: "48px 24px" }}>
      <h1 style={{ fontSize: "1.75rem", marginBottom: "8px" }}>API Reference</h1>
      <p style={{ color: "var(--muted)", marginBottom: "8px" }}>
        Base URL: <code>{base}/api/v1</code>
      </p>
      <p style={{ color: "var(--muted)", marginBottom: "24px", fontSize: "0.9rem" }}>
        All authenticated endpoints require <code>Authorization: Bearer &lt;token&gt;</code>.
        Tokens can be session tokens (from login) or API keys (from Settings).
      </p>

      {/* Quick nav */}
      <div style={{
        display: "flex", gap: "6px", marginBottom: "32px", flexWrap: "wrap",
      }}>
        {nav.map((n) => (
          <a key={n.id} href={`#${n.id}`}
            style={{
              padding: "6px 14px", borderRadius: "6px", fontSize: "0.85rem",
              border: "1px solid var(--line)", textDecoration: "none",
              background: "var(--surface)",
            }}
            onClick={() => setActiveSection(n.id)}
          >{n.label}</a>
        ))}
      </div>

      {/* ── Auth ── */}
      <SectionBlock id="auth" title="Authentication">
        <EndpointDetail method="POST" path="/auth/login" auth="Public" desc="Login with username and password.">
          <Block title="Request">{`{
  "username": "admin",
  "password": "your-password"
}`}</Block>
          <Block title="Response 200">{`{
  "token": "session-token-string",
  "username": "admin",
  "role": "admin"
}`}</Block>
          <Block title="Example">{`curl -X POST ${base}/api/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"username": "admin", "password": "your-password"}'`}</Block>
        </EndpointDetail>

        <EndpointDetail method="POST" path="/auth/register" auth="Public" desc="Create an account. Auto-logs in and returns a session token.">
          <Block title="Request">{`{
  "username": "newuser",
  "password": "securepass"
}`}</Block>
          <Block title="Response 200">{`{
  "token": "session-token-string",
  "username": "newuser",
  "role": "reader"
}`}</Block>
          <p style={{ fontSize: "0.85rem", color: "var(--muted)", marginBottom: "12px" }}>
            Username: 3+ chars, alphanumeric/hyphens/underscores. Password: 6+ chars. Returns <code>409</code> if taken.
          </p>
        </EndpointDetail>

        <EndpointDetail method="POST" path="/auth/logout" auth="Optional" desc="Invalidate the current session token.">
          <Block title="Response 200">{`{ "detail": "Logged out." }`}</Block>
        </EndpointDetail>

        <EndpointDetail method="GET" path="/whoami" auth="Required" desc="Current user info. Compatible with ClawHub CLI.">
          <Block title="Response 200">{`{
  "user": {
    "handle": "admin",
    "displayName": "admin",
    "image": null
  },
  "username": "admin",
  "role": "admin",
  "handle": "admin"
}`}</Block>
        </EndpointDetail>
      </SectionBlock>

      {/* ── Skills ── */}
      <SectionBlock id="skills" title="Skills">
        <EndpointDetail method="GET" path="/skills" auth="Required" desc="List all skills, newest first.">
          <p style={{ fontSize: "0.85rem", marginBottom: "8px" }}>
            Query: <code>?limit=50&cursor=...</code> (limit 1-100)
          </p>
          <Block title="Response 200">{`{
  "items": [{
    "slug": "git-essentials",
    "displayName": "Git Essentials",
    "summary": "Essential Git commands...",
    "tags": ["latest"],
    "stats": { "downloads": 0, "stars": 0 },
    "createdAt": 1711500000000,
    "updatedAt": 1711500000000,
    "latestVersion": {
      "version": "1.1.0",
      "createdAt": 1711500000000,
      "changelog": null
    }
  }],
  "nextCursor": null
}`}</Block>
        </EndpointDetail>

        <EndpointDetail method="GET" path="/skills/{slug}" auth="Required" desc="Skill detail with owner info.">
          <Block title="Response 200">{`{
  "skill": { "slug": "git-essentials", "displayName": "Git Essentials", ... },
  "latestVersion": { "version": "1.1.0", "createdAt": 1711500000000 },
  "owner": { "handle": "admin", "displayName": "admin" }
}`}</Block>
        </EndpointDetail>

        <EndpointDetail method="GET" path="/skills/{slug}/versions" auth="Required" desc="Version history, newest first.">
          <Block title="Response 200">{`{
  "versions": [
    { "version": "1.1.0", "createdAt": 1711500000000, "changelog": "Bug fixes" },
    { "version": "1.0.0", "createdAt": 1711400000000, "changelog": "Initial release" }
  ]
}`}</Block>
        </EndpointDetail>

        <EndpointDetail method="GET" path="/search?q=&limit=" auth="Required" desc="Search skills by name, slug, or summary.">
          <Block title="Example">{`curl -H "Authorization: Bearer <token>" \\
  "${base}/api/v1/search?q=git&limit=10"`}</Block>
          <Block title="Response 200">{`{
  "results": [{
    "slug": "git-essentials",
    "displayName": "Git Essentials",
    "summary": "...",
    "version": "1.1.0",
    "score": 1.0,
    "updatedAt": 1711500000000
  }]
}`}</Block>
        </EndpointDetail>

        <EndpointDetail method="GET" path="/resolve?slug=&hash=" auth="Required" desc="Resolve latest version. Used by clawhub CLI during install.">
          <Block title="Response 200">{`{
  "match": { "version": "1.0.0" },
  "latestVersion": { "version": "1.1.0", "createdAt": 1711500000000 }
}`}</Block>
        </EndpointDetail>

        <EndpointDetail method="GET" path="/download?slug=&version=" auth="Required" desc="Download skill as zip archive.">
          <p style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
            Returns <code>application/zip</code> binary. Both <code>slug</code> and <code>version</code> required.
          </p>
        </EndpointDetail>

        <EndpointDetail method="POST" path="/skills" auth="Publisher or Admin" desc="Publish a skill. Accepts two multipart formats.">
          <p style={{ fontSize: "0.85rem", fontWeight: 600, marginBottom: "8px" }}>Format 1: clawhub CLI (payload + files)</p>
          <Block title="Form fields">{`payload: JSON string {"slug", "version", "displayName", "description", "changelog", "tags"}
files: one or more skill files (assembled into zip server-side)`}</Block>
          <p style={{ fontSize: "0.85rem", fontWeight: 600, marginBottom: "8px" }}>Format 2: Direct upload (slug + version + file)</p>
          <Block title="Form fields">{`slug: skill-slug
version: 1.0.0
display_name: My Skill (optional)
summary: Short description (optional)
changelog: What changed (optional)
tags: comma,separated (optional)
file: skill.zip`}</Block>
          <Block title="Response 200">{`{
  "ok": true,
  "skillId": "git-essentials",
  "versionId": "git-essentials@1.0.0",
  "slug": "git-essentials",
  "version": "1.0.0",
  "message": "Published successfully"
}`}</Block>
        </EndpointDetail>

        <EndpointDetail method="DELETE" path="/skills/{slug}" auth="Admin only" desc="Soft-delete a skill.">
          <Block title="Response 200">{`{ "message": "Skill deleted" }`}</Block>
        </EndpointDetail>
      </SectionBlock>

      {/* ── API Keys ── */}
      <SectionBlock id="keys" title="API Keys">
        <EndpointDetail method="GET" path="/auth/keys" auth="Required" desc="List your active API keys.">
          <Block title="Response 200">{`[{
  "keyId": "abc12345",
  "label": "my-laptop",
  "tokenPrefix": "abc12345abcd",
  "createdAt": 1711500000000
}]`}</Block>
        </EndpointDetail>

        <EndpointDetail method="POST" path="/auth/keys" auth="Required" desc="Generate a new API key. Max 10 per user.">
          <Block title="Request">{`{ "label": "CI pipeline" }`}</Block>
          <Block title="Response 200">{`{
  "keyId": "abc12345",
  "label": "CI pipeline",
  "token": "full-key-shown-only-once",
  "createdAt": 1711500000000
}`}</Block>
        </EndpointDetail>

        <EndpointDetail method="DELETE" path="/auth/keys/{keyId}" auth="Required" desc="Revoke an API key immediately.">
          <Block title="Response 200">{`{ "detail": "API key revoked." }`}</Block>
        </EndpointDetail>
      </SectionBlock>

      {/* ── Admin ── */}
      <SectionBlock id="admin" title="Admin">
        <p style={{ color: "var(--muted)", fontSize: "0.9rem", marginBottom: "20px" }}>All admin endpoints require <strong>admin</strong> role.</p>

        <EndpointDetail method="GET" path="/admin/settings/proxy" auth="Admin" desc="Get proxy configuration.">
          <Block title="Response 200">{`{
  "enabled": false,
  "upstreamUrl": "https://clawhub.ai"
}`}</Block>
        </EndpointDetail>

        <EndpointDetail method="PUT" path="/admin/settings/proxy" auth="Admin" desc="Enable or disable the public ClawHub proxy.">
          <Block title="Request">{`{
  "enabled": true,
  "upstream_url": "https://clawhub.ai"
}`}</Block>
          <Block title="Response 200">{`{
  "enabled": true,
  "upstreamUrl": "https://clawhub.ai"
}`}</Block>
          <p style={{ fontSize: "0.85rem", color: "var(--muted)", marginBottom: "12px" }}>
            When enabled, resolve/download/search/detail endpoints proxy to upstream for skills not found locally. Cached skills remain accessible after disabling.
          </p>
        </EndpointDetail>

        <EndpointDetail method="POST" path="/admin/users" auth="Admin" desc="Create a new user.">
          <Block title="Request">{`{
  "username": "publisher1",
  "password": "securepass",
  "role": "publisher"
}`}</Block>
          <Block title="Response 200">{`{
  "user": { "username": "publisher1", "role": "publisher", "isActive": true, "createdAt": ... },
  "apiToken": "generated-api-token"
}`}</Block>
        </EndpointDetail>

        <EndpointDetail method="GET" path="/admin/users" auth="Admin" desc="List all users.">
          <Block title="Response 200">{`[
  { "username": "admin", "role": "admin", "isActive": true, "createdAt": ... },
  { "username": "publisher1", "role": "publisher", "isActive": true, "createdAt": ... }
]`}</Block>
        </EndpointDetail>

        <EndpointDetail method="DELETE" path="/admin/users/{username}" auth="Admin" desc="Deactivate a user. Tokens stop working.">
          <Block title="Response 200">{`{ "detail": "User publisher1 has been deactivated." }`}</Block>
        </EndpointDetail>

        <EndpointDetail method="GET" path="/admin/policies" auth="Admin" desc="List admission policies.">
          <Block title="Response 200">{`{
  "policies": [{
    "id": "my-skill", "slug": "my-skill",
    "allowedVersions": ">=1.0.0", "policyType": "allow",
    "approvedBy": "admin", "notes": "Approved", "createdAt": ...
  }]
}`}</Block>
        </EndpointDetail>

        <EndpointDetail method="POST" path="/admin/policies" auth="Admin" desc="Create admission policy.">
          <Block title="Request">{`{ "slug": "skill-slug", "policyType": "allow", "allowedVersions": ">=1.0.0", "notes": "optional" }`}</Block>
        </EndpointDetail>

        <EndpointDetail method="PATCH" path="/admin/policies/{slug}" auth="Admin" desc="Update policy.">
          <Block title="Request">{`{ "policyType": "deny", "notes": "Blocked after audit" }`}</Block>
        </EndpointDetail>

        <EndpointDetail method="DELETE" path="/admin/policies/{slug}" auth="Admin" desc="Delete policy." >
          <Block title="Response 200">{`{ "detail": "Policy for 'my-skill' deleted." }`}</Block>
        </EndpointDetail>

        <EndpointDetail method="GET" path="/admin/policies/pending" auth="Admin" desc="List pending approval requests.">
          <Block title="Response 200">{`{
  "requests": [{
    "id": "slug::timestamp", "slug": "my-skill",
    "requestedBy": "user1", "requestedAt": ..., "reason": "...", "status": "pending"
  }]
}`}</Block>
        </EndpointDetail>

        <EndpointDetail method="POST" path="/admin/policies/pending/{id}/approve" auth="Admin" desc="Approve pending request (creates allow policy)." >
          <span />
        </EndpointDetail>

        <EndpointDetail method="POST" path="/admin/policies/pending/{id}/deny" auth="Admin" desc="Deny pending request." >
          <span />
        </EndpointDetail>
      </SectionBlock>

      {/* ── Discovery ── */}
      <SectionBlock id="discovery" title="Discovery & Health">
        <EndpointDetail method="GET" path="/.well-known/clawhub.json" auth="Public" desc="Registry discovery. Used by clawhub CLI to find the API.">
          <Block title="Response 200">{`{ "apiBase": "${base}" }`}</Block>
          <p style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
            The CLI appends <code>/api/v1</code> to <code>apiBase</code> for all requests.
          </p>
        </EndpointDetail>

        <EndpointDetail method="GET" path="/healthz" auth="Public" desc="Health check for database and storage.">
          <Block title="Response 200">{`{ "status": "ok", "checks": { "database": "ok", "storage": "ok" } }`}</Block>
          <p style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
            Returns <code>503</code> with <code>"status": "degraded"</code> if any check fails.
          </p>
        </EndpointDetail>
      </SectionBlock>

      {/* ── Error format ── */}
      <SectionBlock id="errors" title="Error Format">
        <Block title="Standard error">{`{ "detail": "Human-readable error message" }`}</Block>
        <Block title="Validation error (422)">{`{
  "detail": [
    { "type": "missing", "loc": ["body", "slug"], "msg": "Field required" }
  ]
}`}</Block>
        <div style={{ marginTop: "16px" }}>
          <table style={{ width: "100%", fontSize: "0.85rem", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "2px solid var(--line)" }}>
                <th style={{ padding: "8px 0" }}>Code</th>
                <th style={{ padding: "8px 0" }}>Meaning</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["200", "Success"],
                ["400", "Bad request / validation"],
                ["401", "Missing or invalid token"],
                ["403", "Insufficient role"],
                ["404", "Resource not found"],
                ["409", "Conflict (duplicate)"],
                ["422", "FastAPI validation error"],
                ["503", "Service degraded"],
              ].map(([code, desc]) => (
                <tr key={code} style={{ borderBottom: "1px solid var(--line)" }}>
                  <td style={{ padding: "6px 0" }}><code>{code}</code></td>
                  <td style={{ padding: "6px 0" }}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionBlock>
    </main>
  );
}
