import { useEffect, useState } from "react";
import {
  listUsers,
  createUser,
  updateUserRole,
  deleteUser,
  listPolicies,
  createPolicy,
  updatePolicy,
  deletePolicy,
  whoami,
  getProxySettings,
  updateProxySettings,
  type UserSchema,
  type AdmissionPolicy,
  type ProxySettings,
} from "../lib/api";

export function Admin() {
  const [users, setUsers] = useState<UserSchema[]>([]);
  const [policies, setPolicies] = useState<AdmissionPolicy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [checked, setChecked] = useState(false);

  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState("reader");
  const [newPolicySlug, setNewPolicySlug] = useState("");
  const [newPolicyType, setNewPolicyType] = useState("allow");
  const [editingPolicy, setEditingPolicy] = useState<string | null>(null);
  const [editPolicyType, setEditPolicyType] = useState("");
  const [editPolicyNotes, setEditPolicyNotes] = useState("");
  const [proxyEnabled, setProxyEnabled] = useState(false);
  const [proxyUrl, setProxyUrl] = useState("https://clawhub.ai");
  const [proxyToggling, setProxyToggling] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("clawhub-token");
    if (!token) {
      setChecked(true);
      setLoading(false);
      return;
    }

    whoami()
      .then((me) => {
        if (me.role === "admin") {
          setIsAdmin(true);
          return Promise.all([listUsers(), listPolicies(), getProxySettings()]);
        }
        return null;
      })
      .then((result) => {
        if (result) {
          setUsers(result[0]);
          setPolicies(result[1].policies);
          setProxyEnabled(result[2].enabled);
          setProxyUrl(result[2].upstreamUrl);
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"))
      .finally(() => {
        setChecked(true);
        setLoading(false);
      });
  }, []);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createUser({ username: newUsername, password: newPassword, role: newRole });
      const result = await listUsers();
      setUsers(result);
      setNewUsername("");
      setNewPassword("");
      setNewRole("reader");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create user");
    }
  };

  const handleChangeRole = async (username: string, newRole: string) => {
    try {
      const updated = await updateUserRole(username, newRole);
      setUsers((prev) => prev.map((u) => u.username === username ? updated : u));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to update role");
    }
  };

  const handleDeleteUser = async (username: string) => {
    if (!confirm("Deactivate this user?")) return;
    try {
      await deleteUser(username);
      setUsers((prev) => prev.filter((u) => u.username !== username));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to deactivate user");
    }
  };

  const handleCreatePolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createPolicy({ slug: newPolicySlug, policy_type: newPolicyType });
      const result = await listPolicies();
      setPolicies(result.policies);
      setNewPolicySlug("");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create policy");
    }
  };

  const handleEditPolicy = (policy: AdmissionPolicy) => {
    setEditingPolicy(policy.slug);
    setEditPolicyType(policy.policyType);
    setEditPolicyNotes(policy.notes || "");
  };

  const handleSavePolicy = async (slug: string) => {
    try {
      const updated = await updatePolicy(slug, {
        policy_type: editPolicyType,
        notes: editPolicyNotes || undefined,
      });
      setPolicies((prev) => prev.map((p) => p.slug === slug ? updated : p));
      setEditingPolicy(null);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to update policy");
    }
  };

  const handleDeletePolicy = async (slug: string) => {
    if (!confirm("Delete this policy?")) return;
    try {
      await deletePolicy(slug);
      setPolicies((prev) => prev.filter((p) => p.slug !== slug));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete policy");
    }
  };

  const handleToggleProxy = async () => {
    setProxyToggling(true);
    try {
      const result = await updateProxySettings({ enabled: !proxyEnabled });
      setProxyEnabled(result.enabled);
      setProxyUrl(result.upstreamUrl);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to update proxy settings");
    } finally {
      setProxyToggling(false);
    }
  };

  if (!checked) return null;

  if (!isAdmin) {
    return (
      <main className="section">
        <div className="card" style={{ textAlign: "center", padding: 40 }}>
          <h2 className="section-title">Admin Access Required</h2>
          <p className="section-subtitle">You must be signed in as an administrator.</p>
        </div>
      </main>
    );
  }

  if (loading) {
    return (
      <main className="section">
        <span className="loading-indicator">Loading...</span>
      </main>
    );
  }

  return (
    <main className="section">
      <h1 className="section-title">Admin Dashboard</h1>
      {error && <div className="error" style={{ marginBottom: 16 }}>{error}</div>}

      {/* Public ClawHub Proxy */}
      <section style={{ marginBottom: 40 }}>
        <h2 className="section-title" style={{ fontSize: "1.3rem" }}>Public ClawHub Proxy</h2>
        <div className="card" style={{ padding: "20px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px", flexWrap: "wrap" }}>
          <div>
            <div style={{ marginBottom: "4px" }}>
              <strong>Upstream passthrough</strong>
              <span style={{
                display: "inline-block", marginLeft: "8px", padding: "2px 8px",
                borderRadius: "4px", fontSize: "0.75rem", fontWeight: 600,
                background: proxyEnabled ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)",
                color: proxyEnabled ? "#16a34a" : "#dc2626",
              }}>
                {proxyEnabled ? "Enabled" : "Disabled"}
              </span>
            </div>
            <div style={{ fontSize: "0.85rem", color: "var(--ink-soft)" }}>
              When enabled, skills not found locally are fetched from the public ClawHub registry and cached.
            </div>
            <div style={{ fontSize: "0.8rem", color: "var(--ink-soft)", marginTop: "4px" }}>
              Upstream: <code>{proxyUrl}</code>
            </div>
          </div>
          <button
            className={proxyEnabled ? "btn btn-danger" : "btn btn-primary"}
            onClick={handleToggleProxy}
            disabled={proxyToggling}
            style={{ whiteSpace: "nowrap" }}
          >
            {proxyToggling ? "Updating..." : proxyEnabled ? "Disable Proxy" : "Enable Proxy"}
          </button>
        </div>
      </section>

      {/* User Management */}
      <section style={{ marginBottom: 40 }}>
        <h2 className="section-title" style={{ fontSize: "1.3rem" }}>User Management</h2>
        <form onSubmit={handleCreateUser} style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
          <input
            className="form-input"
            placeholder="Username"
            value={newUsername}
            onChange={(e) => setNewUsername(e.target.value)}
            required
            style={{ flex: "1 1 140px" }}
          />
          <input
            className="form-input"
            type="password"
            placeholder="Password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            style={{ flex: "1 1 140px" }}
          />
          <select
            className="form-input"
            value={newRole}
            onChange={(e) => setNewRole(e.target.value)}
            style={{ width: "auto" }}
          >
            <option value="reader">Reader</option>
            <option value="publisher">Publisher</option>
            <option value="admin">Admin</option>
          </select>
          <button type="submit" className="btn btn-primary">Create User</button>
        </form>

        <div className="management-list">
          {users.map((u) => (
            <div key={u.username} className="management-item">
              <div className="management-item-main">
                <strong>{u.username}</strong>
                <div style={{ fontSize: "0.85rem", color: "var(--ink-soft)" }}>
                  {u.isActive ? "Active" : "Inactive"} &middot; {new Date(u.createdAt).toLocaleDateString()}
                </div>
              </div>
              <div className="management-actions" style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                <select
                  className="form-input"
                  value={u.role}
                  onChange={(e) => handleChangeRole(u.username, e.target.value)}
                  style={{ width: "auto", fontSize: "0.85rem", padding: "4px 8px" }}
                >
                  <option value="reader">reader</option>
                  <option value="publisher">publisher</option>
                  <option value="admin">admin</option>
                </select>
                {u.isActive && (
                  <button className="btn btn-danger btn-sm" onClick={() => handleDeleteUser(u.username)}>
                    Deactivate
                  </button>
                )}
              </div>
            </div>
          ))}
          {users.length === 0 && (
            <div className="card" style={{ textAlign: "center", color: "var(--ink-soft)" }}>No users found</div>
          )}
        </div>
      </section>

      {/* Admission Policies */}
      <section>
        <h2 className="section-title" style={{ fontSize: "1.3rem" }}>Admission Policies</h2>
        <form onSubmit={handleCreatePolicy} style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
          <input
            className="form-input"
            placeholder="Skill slug"
            value={newPolicySlug}
            onChange={(e) => setNewPolicySlug(e.target.value)}
            required
            style={{ flex: "1 1 200px" }}
          />
          <select
            className="form-input"
            value={newPolicyType}
            onChange={(e) => setNewPolicyType(e.target.value)}
            style={{ width: "auto" }}
          >
            <option value="allow">Allow</option>
            <option value="deny">Deny</option>
          </select>
          <button type="submit" className="btn btn-primary">Add Policy</button>
        </form>

        <div className="management-list">
          {policies.map((policy) => (
            <div key={policy.id} className="management-item">
              {editingPolicy === policy.slug ? (
                <>
                  <div className="management-item-main" style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    <strong>{policy.slug}</strong>
                    <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
                      <select
                        className="form-input"
                        value={editPolicyType}
                        onChange={(e) => setEditPolicyType(e.target.value)}
                        style={{ width: "auto", fontSize: "0.85rem", padding: "4px 8px" }}
                      >
                        <option value="allow">Allow</option>
                        <option value="deny">Deny</option>
                      </select>
                      <input
                        className="form-input"
                        placeholder="Notes (optional)"
                        value={editPolicyNotes}
                        onChange={(e) => setEditPolicyNotes(e.target.value)}
                        style={{ flex: "1 1 150px", fontSize: "0.85rem", padding: "4px 8px" }}
                      />
                    </div>
                  </div>
                  <div className="management-actions" style={{ display: "flex", gap: "8px" }}>
                    <button className="btn btn-primary btn-sm" onClick={() => handleSavePolicy(policy.slug)}>
                      Save
                    </button>
                    <button className="btn btn-sm" onClick={() => setEditingPolicy(null)}>
                      Cancel
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <div className="management-item-main">
                    <strong>{policy.slug}</strong>
                    <div style={{ fontSize: "0.85rem", color: "var(--ink-soft)" }}>
                      {policy.policyType} &middot; approved by {policy.approvedBy || "\u2014"}
                      {policy.notes && ` \u00b7 ${policy.notes}`}
                    </div>
                  </div>
                  <div className="management-actions" style={{ display: "flex", gap: "8px" }}>
                    <button className="btn btn-sm" onClick={() => handleEditPolicy(policy)}>
                      Edit
                    </button>
                    <button className="btn btn-danger btn-sm" onClick={() => handleDeletePolicy(policy.slug)}>
                      Delete
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
          {policies.length === 0 && (
            <div className="card" style={{ textAlign: "center", color: "var(--ink-soft)" }}>No policies found</div>
          )}
        </div>
      </section>
    </main>
  );
}
