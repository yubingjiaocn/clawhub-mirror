import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listSkills, type SkillListItem } from "../lib/api";
import { SkillCard } from "../components/SkillCard";
import { InstallCommand } from "../components/InstallCommand";

export function Home() {
  const [featuredSkills, setFeaturedSkills] = useState<SkillListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    listSkills({ limit: 6 })
      .then((result) => {
        if (cancelled) return;
        setFeaturedSkills(result.items);
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
            <span className="hero-badge">Self-hosted. Enterprise-ready.</span>
            <h1 className="hero-title">Your private agent skill registry.</h1>
            <p className="hero-subtitle">
              Publish, version, and install AgentSkills with the{" "}
              <a href="https://docs.openclaw.ai/tools/clawhub" target="_blank" rel="noreferrer" style={{ textDecoration: "underline" }}>clawhub</a> CLI
              or <a href="https://docs.openclaw.ai/cli#skills" target="_blank" rel="noreferrer" style={{ textDecoration: "underline" }}>openclaw skills</a>.
              Every command below is copy-paste ready.
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
              <div className="stat">Click any command to copy:</div>
              <InstallCommand slug="my-skill" />
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <h2 className="section-title">Recent skills</h2>
        <p className="section-subtitle">Latest skills published to this registry.</p>
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
        <div className="section-cta">
          <Link to="/skills" className="btn">See all skills</Link>
        </div>
      </section>
    </main>
  );
}
