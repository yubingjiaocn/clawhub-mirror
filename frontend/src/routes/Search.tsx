import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { searchSkills, type Skill } from "../lib/api";
import { SkillCard } from "../components/SkillCard";

export function Search() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState(searchParams.get("q") || "");

  useEffect(() => {
    const q = searchParams.get("q");
    if (q) {
      setSearchQuery(q);
      performSearch(q);
    }
  }, [searchParams]);

  const performSearch = async (query: string) => {
    if (!query.trim()) {
      setSkills([]);
      return;
    }
    try {
      setLoading(true);
      const result = await searchSkills(query);
      setSkills(result.skills);
    } catch {
      setSkills([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      setSearchParams({ q: searchQuery.trim() });
    }
  };

  return (
    <main className="section">
      <h1 className="section-title">Search Skills</h1>
      <form onSubmit={handleSubmit} className="search-bar" style={{ marginBottom: 24 }}>
        <span className="mono">/</span>
        <input
          className="search-input"
          placeholder="Search skills..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          autoFocus
        />
        <button type="submit" className="btn btn-primary">Search</button>
      </form>

      {loading ? (
        <span className="loading-indicator">Searching...</span>
      ) : searchParams.get("q") && skills.length > 0 ? (
        <>
          <p className="section-subtitle">
            Found {skills.length} {skills.length === 1 ? "skill" : "skills"}
          </p>
          <div className="grid">
            {skills.map((skill) => (
              <SkillCard key={skill.slug} skill={skill} />
            ))}
          </div>
        </>
      ) : searchParams.get("q") ? (
        <div className="card" style={{ textAlign: "center", color: "var(--ink-soft)" }}>
          No skills found matching &ldquo;{searchParams.get("q")}&rdquo;
        </div>
      ) : (
        <p className="section-subtitle">Enter a search query to find skills.</p>
      )}
    </main>
  );
}
