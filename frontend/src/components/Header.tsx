import { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { applyTheme, useThemeMode } from "../lib/theme";
import { whoami } from "../lib/api";

export default function Header() {
  const { mode: themeMode, setMode: setThemeMode } = useThemeMode();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [user, setUser] = useState<{ username: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const menuRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem("clawhub-token");
    if (token) {
      whoami()
        .then((data) => setUser(data))
        .catch(() => {
          localStorage.removeItem("clawhub-token");
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMobileMenuOpen(false);
      }
    }
    if (mobileMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [mobileMenuOpen]);

  const setTheme = (next: "system" | "light" | "dark") => {
    applyTheme(next);
    setThemeMode(next);
  };

  const handleSignIn = () => {
    const token = prompt("Enter your API token:");
    if (token) {
      localStorage.setItem("clawhub-token", token);
      window.location.reload();
    }
  };

  const handleSignOut = () => {
    localStorage.removeItem("clawhub-token");
    setUser(null);
    navigate("/");
  };

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <Link to="/" className="brand">
          <span className="brand-mark">
            <img src="/clawd-logo.svg" alt="" aria-hidden="true" />
          </span>
          <span className="brand-name">ClawHub Mirror</span>
        </Link>

        <nav className="nav-links">
          <Link to="/skills">Skills</Link>
          <Link to="/search">Search</Link>
        </nav>

        <div className="nav-actions">
          <div className="nav-mobile">
            <button
              className="nav-mobile-trigger"
              type="button"
              aria-label="Open menu"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              <span style={{ fontSize: "1.2rem" }}>&#9776;</span>
            </button>
          </div>

          <div className="theme-toggle">
            <button
              type="button"
              data-state={themeMode === "system" ? "on" : "off"}
              onClick={() => setTheme("system")}
              aria-label="System theme"
              title="System"
            >
              &#9881;
            </button>
            <button
              type="button"
              data-state={themeMode === "light" ? "on" : "off"}
              onClick={() => setTheme("light")}
              aria-label="Light theme"
              title="Light"
            >
              &#9788;
            </button>
            <button
              type="button"
              data-state={themeMode === "dark" ? "on" : "off"}
              onClick={() => setTheme("dark")}
              aria-label="Dark theme"
              title="Dark"
            >
              &#9790;
            </button>
          </div>

          {!loading && (
            <>
              {user ? (
                <button className="user-trigger" type="button" onClick={handleSignOut}>
                  <span className="user-menu-fallback">
                    {user.username.charAt(0).toUpperCase()}
                  </span>
                  <span className="mono">@{user.username}</span>
                  <span className="user-menu-chevron">&#9662;</span>
                </button>
              ) : (
                <button className="btn btn-primary" type="button" onClick={handleSignIn}>
                  <span className="sign-in-label">Sign in</span>
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {mobileMenuOpen && (
        <div ref={menuRef} style={{
          background: "var(--surface)",
          borderTop: "1px solid var(--line)",
          padding: "12px 28px",
          display: "grid",
          gap: "8px",
        }}>
          <Link to="/skills" onClick={() => setMobileMenuOpen(false)}>Skills</Link>
          <Link to="/search" onClick={() => setMobileMenuOpen(false)}>Search</Link>
          {user ? (
            <button type="button" className="btn" onClick={handleSignOut}>Sign out</button>
          ) : (
            <button type="button" className="btn btn-primary" onClick={handleSignIn}>Sign in</button>
          )}
        </div>
      )}
    </header>
  );
}
