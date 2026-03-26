import { useEffect, useState } from "react";
import {
  listUsers,
  createUser,
  deleteUser,
  listPolicies,
  createPolicy,
  deletePolicy,
  whoami,
  type UserSchema,
  type AdmissionPolicy,
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
          return Promise.all([listUsers(), listPolicies()]);
        }
        return null;
      })
      .then((result) => {
        if (result) {
          setUsers(result[0]);
          setPolicies(result[1].policies);
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

  const handleDeletePolicy = async (slug: string) => {
    if (!confirm("Delete this policy?")) return;
    try {
      await deletePolicy(slug);
      setPolicies((prev) => prev.filter((p) => p.slug !== slug));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete policy");
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
          {users.map((user) => (
            <div key={user.username} className="management-item">
              <div className="management-item-main">
                <strong>{user.username}</strong>
                <div style={{ fontSize: "0.85rem", color: "var(--ink-soft)" }}>
                  {user.role} &middot; {user.isActive ? "Active" : "Inactive"} &middot; {new Date(user.createdAt).toLocaleDateString()}
                </div>
              </div>
              <div className="management-actions">
                <button className="btn btn-danger btn-sm" onClick={() => handleDeleteUser(user.username)}>
                  Deactivate
                </button>
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
              <div className="management-item-main">
                <strong>{policy.slug}</strong>
                <div style={{ fontSize: "0.85rem", color: "var(--ink-soft)" }}>
                  {policy.policyType} &middot; approved by {policy.approvedBy || "\u2014"}
                  {policy.notes && ` \u00b7 ${policy.notes}`}
                </div>
              </div>
              <div className="management-actions">
                <button className="btn btn-danger btn-sm" onClick={() => handleDeletePolicy(policy.slug)}>
                  Delete
                </button>
              </div>
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
