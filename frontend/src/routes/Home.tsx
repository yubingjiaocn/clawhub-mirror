import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listSkills, type Skill } from "../lib/api";
import { SkillCard } from "../components/SkillCard";
import { InstallCommand } from "../components/InstallCommand";

export function Home() {
  const [featuredSkills, setFeaturedSkills] = useState<Skill[]>([]);
  const [popularSkills, setPopularSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    Promise.all([
      listSkills({ limit: 6 }),
      listSkills({ limit: 6, sort: "downloads" }),
    ])
      .then(([featured, popular]) => {
        if (cancelled) return;
        setFeaturedSkills(featured.skills);
        setPopularSkills(popular.skills);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, []);

  return (
    <main>
      <section className="hero">
        <div className="hero-inner">
          <div className="hero-copy fade-up" data-delay="1">
            <span className="hero-badge">Lobster-light. Agent-right.</span>
            <h1 className="hero-title">ClawHub Mirror, the skill dock for sharp agents.</h1>
            <p className="hero-subtitle">
              Upload AgentSkills bundles, version them like npm, and make them searchable with
              vectors. No gatekeeping, just signal.
            </p>
            <div style={{ display: "flex", gap: 12, marginTop: 20 }}>
              <Link to="/publish" className="btn btn-primary">
                Publish Skill
              </Link>
              <Link to="/skills" className="btn">
                Browse skills
              </Link>
            </div>
          </div>
          <div className="hero-card hero-search-card fade-up" data-delay="2">
            <div className="hero-install" style={{ marginTop: 18 }}>
              <div className="stat">Search skills. Versioned, rollback-ready.</div>
              <InstallCommand slug="sonoscli" />
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <h2 className="section-title">Featured skills</h2>
        <p className="section-subtitle">Curated signal — highlighted for quick trust.</p>
        <div className="grid">
          {loading ? (
            <div className="card"><span className="loading-indicator">Loading skills...</span></div>
          ) : featuredSkills.length === 0 ? (
            <div className="card">No highlighted skills yet.</div>
          ) : (
            featuredSkills.map((skill) => (
              <SkillCard key={skill.slug} skill={skill} />
            ))
          )}
        </div>
      </section>

      <section className="section">
        <h2 className="section-title">Popular skills</h2>
        <p className="section-subtitle">Most-downloaded picks.</p>
        <div className="grid">
          {loading ? (
            <div className="card"><span className="loading-indicator">Loading skills...</span></div>
          ) : popularSkills.length === 0 ? (
            <div className="card">No skills yet. Be the first.</div>
          ) : (
            popularSkills.map((skill) => (
              <SkillCard key={skill.slug} skill={skill} />
            ))
          )}
        </div>
        <div className="section-cta">
          <Link to="/skills" className="btn">See all skills</Link>
        </div>
      </section>
    </main>
  );
}
