import { useEffect, useState, useCallback } from "react";
import { listSkills, type Skill } from "../lib/api";
import { SkillCard } from "../components/SkillCard";

type SortOption = "newest" | "downloads" | "name";

export function Skills() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<SortOption>("downloads");
  const [cursor, setCursor] = useState<string | undefined>();
  const [hasMore, setHasMore] = useState(false);

  const fetchSkills = useCallback(async (reset: boolean) => {
    try {
      setLoading(true);
      const sortMap: Record<SortOption, string> = {
        newest: "createdAt",
        downloads: "downloads",
        name: "name",
      };
      const result = await listSkills({
        limit: 12,
        sort: sortMap[sortBy],
        cursor: reset ? undefined : cursor,
      });
      if (reset) {
        setSkills(result.skills);
      } else {
        setSkills((prev) => [...prev, ...result.skills]);
      }
      setCursor(result.nextCursor);
      setHasMore(!!result.nextCursor);
    } catch {
      // Silently handle — empty state shown
    } finally {
      setLoading(false);
    }
  }, [sortBy, cursor]);

  useEffect(() => {
    fetchSkills(true);
  }, [sortBy]);

  const filtered = searchQuery
    ? skills.filter(
        (s) =>
          s.displayName.toLowerCase().includes(searchQuery.toLowerCase()) ||
          s.slug.toLowerCase().includes(searchQuery.toLowerCase()) ||
          s.summary?.toLowerCase().includes(searchQuery.toLowerCase()),
      )
    : skills;

  return (
    <main className="section">
      <header className="skills-header-top">
        <h1 className="section-title" style={{ marginBottom: 8 }}>
          Skills
          {skills.length > 0 && (
            <span style={{ opacity: 0.55 }}>{` (${skills.length})`}</span>
          )}
        </h1>
        <p className="section-subtitle" style={{ marginBottom: 0 }}>
          Browse the skill library.
        </p>
      </header>

      <div className="skills-container">
        <div className="skills-toolbar">
          <div className="skills-search">
            <input
              className="skills-search-input"
              type="text"
              placeholder="Filter skills..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div className="skills-toolbar-row">
            <select
              className="skills-sort"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortOption)}
            >
              <option value="downloads">Downloads</option>
              <option value="newest">Newest</option>
              <option value="name">Name</option>
            </select>
          </div>
        </div>

        {loading && skills.length === 0 ? (
          <div className="card"><span className="loading-indicator">Loading skills...</span></div>
        ) : filtered.length === 0 ? (
          <div className="card" style={{ textAlign: "center", color: "var(--ink-soft)" }}>
            {searchQuery ? `No skills matching "${searchQuery}"` : "No skills available yet."}
          </div>
        ) : (
          <>
            <div className="grid">
              {filtered.map((skill) => (
                <SkillCard key={skill.slug} skill={skill} />
              ))}
            </div>
            {hasMore && (
              <div className="section-cta" style={{ marginTop: 24 }}>
                <button
                  className="btn"
                  onClick={() => fetchSkills(false)}
                  disabled={loading}
                >
                  {loading ? "Loading..." : "Load more"}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </main>
  );
}
