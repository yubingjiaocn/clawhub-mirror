import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  getSkill,
  getVersions,
  downloadSkill,
  type SkillDetailResponse,
  type VersionInfo,
} from "../lib/api";
import { InstallCommand } from "../components/InstallCommand";

export function SkillDetail() {
  const { slug } = useParams<{ slug: string }>();
  const [detail, setDetail] = useState<SkillDetailResponse | null>(null);
  const [versions, setVersions] = useState<VersionInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"readme" | "versions">("readme");

  useEffect(() => {
    if (!slug) return;
    let cancelled = false;
    setLoading(true);

    Promise.all([getSkill(slug), getVersions(slug)])
      .then(([skillData, versionsData]) => {
        if (cancelled) return;
        setDetail(skillData);
        setVersions(versionsData.versions);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load skill");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [slug]);

  if (loading) {
    return (
      <main className="section">
        <span className="loading-indicator">Loading skill...</span>
      </main>
    );
  }

  if (error || !detail) {
    return (
      <main className="section">
        <div className="card">
          <p className="error">{error || "Skill not found"}</p>
        </div>
      </main>
    );
  }

  const { skill, latestVersion, owner } = detail;

  return (
    <main className="section">
      <div className="skill-detail-stack">
        {/* Hero */}
        <div className="card skill-hero">
          <div className="skill-hero-header">
            <div className="skill-hero-title">
              <div className="skill-hero-title-row">
                <h1 className="section-title" style={{ margin: 0 }}>
                  {skill.displayName}
                </h1>
                {skill.tags?.map((t) => (
                  <span key={t} className="tag">{t}</span>
                ))}
              </div>
              <p style={{ color: "var(--ink-soft)", margin: 0 }}>
                {skill.summary}
              </p>
              <div className="stat">
                by <strong>{owner.handle}</strong> &middot; &#9733; {skill.stats.stars} &middot; &#8595; {skill.stats.downloads}
              </div>
            </div>
            <div className="skill-hero-cta">
              {latestVersion && (
                <>
                  <div className="skill-version-pill">
                    <span className="skill-version-label">Latest</span>
                    <strong>v{latestVersion.version}</strong>
                  </div>
                  <a className="btn btn-primary" href={downloadSkill(slug!, latestVersion.version)}>
                    Download .zip
                  </a>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Install */}
        <div className="card">
          <InstallCommand slug={slug!} />
        </div>

        {/* Tabs */}
        <div className="card tab-card">
          <div className="tab-header">
            <button
              className={`tab-button ${activeTab === "readme" ? "is-active" : ""}`}
              onClick={() => setActiveTab("readme")}
            >
              README
            </button>
            <button
              className={`tab-button ${activeTab === "versions" ? "is-active" : ""}`}
              onClick={() => setActiveTab("versions")}
            >
              Versions ({versions.length})
            </button>
          </div>

          {activeTab === "readme" ? (
            <div className="tab-body">
              <div className="markdown">
                {latestVersion?.changelog ? (
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {latestVersion.changelog}
                  </ReactMarkdown>
                ) : (
                  <p style={{ color: "var(--ink-soft)" }}>No README available.</p>
                )}
              </div>
            </div>
          ) : (
            <div className="tab-body">
              <div className="version-scroll">
                <div className="version-list">
                  {versions.map((v) => (
                    <div key={v.version} className="version-row">
                      <div className="version-info">
                        <div>
                          v{v.version} &middot;{" "}
                          {new Date(v.createdAt).toLocaleDateString()}
                        </div>
                        {v.changelog && (
                          <div style={{ color: "var(--ink-soft)", whiteSpace: "pre-wrap" }}>
                            {v.changelog}
                          </div>
                        )}
                      </div>
                      <div className="version-actions">
                        <a
                          className="btn version-zip"
                          href={downloadSkill(slug!, v.version)}
                        >
                          Zip
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
