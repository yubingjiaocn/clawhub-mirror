import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  whoami,
  listApiKeys,
  createApiKey,
  revokeApiKey,
  type ApiKey,
  type WhoamiResponse,
} from "../lib/api";

export function Settings() {
  const navigate = useNavigate();
  const [user, setUser] = useState<WhoamiResponse | null>(null);
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [newKeyLabel, setNewKeyLabel] = useState("");
  const [createdToken, setCreatedToken] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("clawhub-token");
    if (!token) {
      navigate("/");
      return;
    }
    Promise.all([whoami(), listApiKeys()])
      .then(([me, apiKeys]) => {
        setUser(me);
        setKeys(apiKeys);
      })
      .catch(() => navigate("/"))
      .finally(() => setLoading(false));
  }, [navigate]);

  const handleCreate = async () => {
    setError("");
    setCreating(true);
    setCreatedToken(null);
    try {
      const resp = await createApiKey(newKeyLabel);
      setCreatedToken(resp.token);
      setNewKeyLabel("");
      // Refresh list
      const updated = await listApiKeys();
      setKeys(updated);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create key");
    } finally {
      setCreating(false);
    }
  };

  const handleRevoke = async (keyId: string) => {
    if (!confirm(`Revoke API key ${keyId}...? This cannot be undone.`)) return;
    try {
      await revokeApiKey(keyId);
      setKeys(keys.filter((k) => k.keyId !== keyId));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to revoke key");
    }
  };

  if (loading) {
    return <div className="container" style={{ padding: "48px 24px" }}>Loading...</div>;
  }

  if (!user) return null;

  return (
    <div className="container" style={{ padding: "48px 24px", maxWidth: "720px", margin: "0 auto" }}>
      <h1 style={{ fontSize: "1.5rem", marginBottom: "8px" }}>Settings</h1>
      <p style={{ color: "var(--muted)", marginBottom: "32px" }}>
        Signed in as <strong>@{user.username}</strong> ({user.role})
      </p>

      <section>
        <h2 style={{ fontSize: "1.15rem", marginBottom: "16px" }}>API Keys</h2>
        <p style={{ color: "var(--muted)", fontSize: "0.875rem", marginBottom: "20px" }}>
          API keys are used for CLI and programmatic access. Keep them secret.
        </p>

        {/* Create new key */}
        <div style={{
          display: "flex",
          gap: "8px",
          marginBottom: "20px",
          alignItems: "flex-end",
        }}>
          <div style={{ flex: 1 }}>
            <label htmlFor="key-label" style={{ display: "block", marginBottom: "4px", fontSize: "0.8rem", color: "var(--muted)" }}>
              Label (optional)
            </label>
            <input
              id="key-label"
              type="text"
              placeholder="e.g. CI/CD pipeline"
              value={newKeyLabel}
              onChange={(e) => setNewKeyLabel(e.target.value)}
              style={{
                width: "100%",
                padding: "8px 12px",
                borderRadius: "6px",
                border: "1px solid var(--line)",
                background: "var(--bg)",
                color: "var(--text)",
                fontSize: "0.9rem",
                boxSizing: "border-box",
              }}
            />
          </div>
          <button
            className="btn btn-primary"
            type="button"
            onClick={handleCreate}
            disabled={creating}
            style={{ whiteSpace: "nowrap" }}
          >
            {creating ? "Creating..." : "Generate new key"}
          </button>
        </div>

        {error && (
          <div style={{ color: "var(--red, #e53e3e)", marginBottom: "16px", fontSize: "0.875rem" }}>
            {error}
          </div>
        )}

        {/* Newly created token (shown once) */}
        {createdToken && (
          <div style={{
            background: "var(--surface)",
            border: "1px solid var(--line)",
            borderRadius: "8px",
            padding: "16px",
            marginBottom: "20px",
          }}>
            <p style={{ fontWeight: 600, marginBottom: "8px", fontSize: "0.9rem" }}>
              New API key created. Copy it now — it won't be shown again.
            </p>
            <div style={{
              display: "flex",
              gap: "8px",
              alignItems: "center",
            }}>
              <code style={{
                flex: 1,
                background: "var(--bg)",
                padding: "8px 12px",
                borderRadius: "6px",
                fontSize: "0.85rem",
                wordBreak: "break-all",
                border: "1px solid var(--line)",
              }}>
                {createdToken}
              </code>
              <button
                className="btn"
                type="button"
                onClick={() => {
                  navigator.clipboard.writeText(createdToken);
                }}
                style={{ whiteSpace: "nowrap" }}
              >
                Copy
              </button>
            </div>
          </div>
        )}

        {/* Key list */}
        {keys.length === 0 ? (
          <p style={{ color: "var(--muted)", fontSize: "0.9rem" }}>No API keys yet.</p>
        ) : (
          <div style={{
            border: "1px solid var(--line)",
            borderRadius: "8px",
            overflow: "hidden",
          }}>
            {keys.map((key, i) => (
              <div
                key={key.keyId}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 16px",
                  borderTop: i > 0 ? "1px solid var(--line)" : undefined,
                  gap: "12px",
                }}
              >
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <code style={{ fontSize: "0.85rem" }}>{key.tokenPrefix}...</code>
                    {key.label && (
                      <span style={{ fontSize: "0.8rem", color: "var(--muted)" }}>
                        {key.label}
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "var(--muted)", marginTop: "2px" }}>
                    Created {new Date(key.createdAt).toLocaleDateString()}
                  </div>
                </div>
                <button
                  className="btn"
                  type="button"
                  onClick={() => handleRevoke(key.keyId)}
                  style={{ color: "var(--red, #e53e3e)", fontSize: "0.85rem" }}
                >
                  Revoke
                </button>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
