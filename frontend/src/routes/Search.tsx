import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { searchSkills, type SearchResultItem } from "../lib/api";
import { Link } from "react-router-dom";

export function Search() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [results, setResults] = useState<SearchResultItem[]>([]);
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
      setResults([]);
      return;
    }
    try {
      setLoading(true);
      const data = await searchSkills(query);
      setResults(data.results);
    } catch {
      setResults([]);
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
      ) : searchParams.get("q") && results.length > 0 ? (
        <>
          <p className="section-subtitle">
            Found {results.length} {results.length === 1 ? "skill" : "skills"}
          </p>
          <div className="grid">
            {results.map((r) => (
              <Link to={`/skills/${r.slug}`} key={r.slug} className="card skill-card">
                <h3 className="skill-card-title">{r.displayName}</h3>
                <p className="skill-card-summary">{r.summary || "A fresh skill bundle."}</p>
                <div className="skill-card-footer">
                  <div className="stat">
                    {r.version && <span>v{r.version}</span>}
                  </div>
                </div>
              </Link>
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
