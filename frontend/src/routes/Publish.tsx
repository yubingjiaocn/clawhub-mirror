import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { publishSkill } from "../lib/api";

export function Publish() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [form, setForm] = useState({
    slug: "",
    version: "",
    display_name: "",
    summary: "",
    changelog: "",
    tags: "",
  });

  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const token = localStorage.getItem("clawhub-token");

  const handleInput = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === "dragenter" || e.type === "dragover");
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const f = e.dataTransfer.files?.[0];
    if (f?.name.endsWith(".zip")) {
      setFile(f);
      setError(null);
    } else {
      setError("Please upload a .zip file");
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f?.name.endsWith(".zip")) {
      setFile(f);
      setError(null);
    } else {
      setError("Please upload a .zip file");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) { setError("Please select a file"); return; }
    if (!form.slug || !form.version || !form.display_name) {
      setError("Please fill in all required fields");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const data = new FormData();
      data.append("file", file);
      data.append("slug", form.slug);
      data.append("version", form.version);
      data.append("display_name", form.display_name);
      if (form.summary) data.append("summary", form.summary);
      if (form.changelog) data.append("changelog", form.changelog);
      if (form.tags) data.append("tags", form.tags);
      await publishSkill(data);
      setSuccess(true);
      setTimeout(() => navigate(`/skills/${form.slug}`), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Publish failed");
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <main className="section">
        <div className="card" style={{ textAlign: "center", padding: 40 }}>
          <h2 className="section-title">Sign in required</h2>
          <p className="section-subtitle">You must be signed in to publish skills.</p>
        </div>
      </main>
    );
  }

  if (success) {
    return (
      <main className="section">
        <div className="card" style={{ textAlign: "center", padding: 40 }}>
          <h2 className="section-title" style={{ color: "#1a6b5b" }}>Skill published!</h2>
          <p className="section-subtitle">Redirecting to skill page...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="section">
      <div className="upload-shell">
        <div className="upload-page">
          <div className="upload-page-header">
            <div>
              <h1 className="upload-page-title">Publish a Skill</h1>
              <p className="upload-page-subtitle">
                Share your AgentSkill bundle with the community.
              </p>
            </div>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="upload-grid">
              <div className="upload-panel" style={{ display: "grid", gap: 14, padding: 20, borderRadius: "var(--radius-md)", border: "1px solid var(--line)", background: "var(--surface)" }}>
                <div className="upload-field" style={{ display: "grid", gap: 8 }}>
                  <label htmlFor="slug" className="form-label">Slug *</label>
                  <input id="slug" name="slug" value={form.slug} onChange={handleInput} className="form-input" placeholder="my-skill" required />
                </div>
                <div className="upload-field" style={{ display: "grid", gap: 8 }}>
                  <label htmlFor="version" className="form-label">Version *</label>
                  <input id="version" name="version" value={form.version} onChange={handleInput} className="form-input" placeholder="1.0.0" required />
                </div>
                <div className="upload-field" style={{ display: "grid", gap: 8 }}>
                  <label htmlFor="display_name" className="form-label">Display Name *</label>
                  <input id="display_name" name="display_name" value={form.display_name} onChange={handleInput} className="form-input" placeholder="My Awesome Skill" required />
                </div>
                <div className="upload-field" style={{ display: "grid", gap: 8 }}>
                  <label htmlFor="summary" className="form-label">Summary</label>
                  <textarea id="summary" name="summary" value={form.summary} onChange={handleInput} className="form-input" placeholder="A brief description..." rows={3} />
                </div>
                <div className="upload-field" style={{ display: "grid", gap: 8 }}>
                  <label htmlFor="changelog" className="form-label">Changelog</label>
                  <textarea id="changelog" name="changelog" value={form.changelog} onChange={handleInput} className="form-input" placeholder="What changed in this version..." rows={3} />
                </div>
                <div className="upload-field" style={{ display: "grid", gap: 8 }}>
                  <label htmlFor="tags" className="form-label">Tags</label>
                  <input id="tags" name="tags" value={form.tags} onChange={handleInput} className="form-input" placeholder="web, api, automation" />
                  <span style={{ fontSize: "0.82rem", color: "var(--ink-soft)" }}>Comma-separated</span>
                </div>
              </div>

              <div style={{ display: "grid", gap: 14, alignContent: "start" }}>
                <div
                  className={`upload-dropzone ${dragActive ? "is-dragging" : ""}`}
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  style={{ minHeight: 180 }}
                >
                  <input ref={fileInputRef} type="file" accept=".zip" onChange={handleFileChange} className="upload-file-input" />
                  <div className="upload-dropzone-copy">
                    {file ? (
                      <>
                        <strong>{file.name}</strong>
                        <span className="upload-dropzone-count">{(file.size / 1024).toFixed(1)} KB</span>
                      </>
                    ) : (
                      <>
                        <div className="dropzone-icon" style={{ margin: "0 auto" }}>&#128230;</div>
                        <strong>Drop your .zip here</strong>
                        <span className="upload-dropzone-hint">or click to browse</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {error && <div className="error" style={{ marginTop: 14 }}>{error}</div>}

            <div className="upload-submit-row" style={{ marginTop: 18 }}>
              <div />
              <button type="submit" className="btn btn-primary upload-submit-btn" disabled={loading}>
                {loading ? "Publishing..." : "Publish Skill"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </main>
  );
}
