import { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { applyTheme, useThemeMode } from "../lib/theme";
import { whoami, login, logout } from "../lib/api";

export default function Header() {
  const { mode: themeMode, setMode: setThemeMode } = useThemeMode();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [user, setUser] = useState<{ username: string; role?: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [loginOpen, setLoginOpen] = useState(false);
  const [loginUsername, setLoginUsername] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const loginRef = useRef<HTMLDivElement>(null);
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
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setUserMenuOpen(false);
      }
    }
    if (mobileMenuOpen || userMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [mobileMenuOpen, userMenuOpen]);

  const setTheme = (next: "system" | "light" | "dark") => {
    applyTheme(next);
    setThemeMode(next);
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError("");
    setLoginLoading(true);
    try {
      const resp = await login(loginUsername, loginPassword);
      localStorage.setItem("clawhub-token", resp.token);
      setUser({ username: resp.username, role: resp.role });
      setLoginOpen(false);
      setLoginUsername("");
      setLoginPassword("");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Login failed";
      // Try to parse JSON error detail
      try {
        const parsed = JSON.parse(msg);
        setLoginError(parsed.detail || msg);
      } catch {
        setLoginError(msg);
      }
    } finally {
      setLoginLoading(false);
    }
  };

  const handleSignOut = async () => {
    await logout();
    localStorage.removeItem("clawhub-token");
    setUser(null);
    navigate("/");
  };

  return (
    <>
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
                  <div ref={userMenuRef} style={{ position: "relative" }}>
                    <button className="user-trigger" type="button" onClick={() => setUserMenuOpen(!userMenuOpen)}>
                      <span className="user-menu-fallback">
                        {user.username.charAt(0).toUpperCase()}
                      </span>
                      <span className="mono">@{user.username}</span>
                      <span className="user-menu-chevron">&#9662;</span>
                    </button>
                    {userMenuOpen && (
                      <div style={{
                        position: "absolute",
                        right: 0,
                        top: "calc(100% + 4px)",
                        background: "var(--surface)",
                        border: "1px solid var(--line)",
                        borderRadius: "8px",
                        padding: "4px",
                        minWidth: "160px",
                        zIndex: 100,
                        boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
                      }}>
                        <button
                          type="button"
                          className="btn"
                          style={{ width: "100%", textAlign: "left", borderRadius: "6px" }}
                          onClick={() => { setUserMenuOpen(false); navigate("/settings"); }}
                        >
                          Settings
                        </button>
                        {user.role === "admin" && (
                          <button
                            type="button"
                            className="btn"
                            style={{ width: "100%", textAlign: "left", borderRadius: "6px" }}
                            onClick={() => { setUserMenuOpen(false); navigate("/admin"); }}
                          >
                            Admin
                          </button>
                        )}
                        <button
                          type="button"
                          className="btn"
                          style={{ width: "100%", textAlign: "left", borderRadius: "6px" }}
                          onClick={() => { setUserMenuOpen(false); handleSignOut(); }}
                        >
                          Sign out
                        </button>
                      </div>
                    )}
                  </div>
                ) : (
                  <button className="btn btn-primary" type="button" onClick={() => setLoginOpen(true)}>
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
              <button type="button" className="btn btn-primary" onClick={() => { setMobileMenuOpen(false); setLoginOpen(true); }}>Sign in</button>
            )}
          </div>
        )}
      </header>

      {loginOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
          onClick={(e) => { if (e.target === e.currentTarget) setLoginOpen(false); }}
        >
          <div
            ref={loginRef}
            style={{
              background: "var(--surface)",
              border: "1px solid var(--line)",
              borderRadius: "12px",
              padding: "32px",
              width: "100%",
              maxWidth: "380px",
              boxShadow: "0 8px 32px rgba(0,0,0,0.2)",
            }}
          >
            <h2 style={{ margin: "0 0 24px", fontSize: "1.25rem" }}>Sign in to ClawHub</h2>
            <form onSubmit={handleLogin}>
              <div style={{ marginBottom: "16px" }}>
                <label htmlFor="login-username" style={{ display: "block", marginBottom: "6px", fontSize: "0.875rem", fontWeight: 500 }}>
                  Username
                </label>
                <input
                  id="login-username"
                  type="text"
                  value={loginUsername}
                  onChange={(e) => setLoginUsername(e.target.value)}
                  required
                  autoFocus
                  autoComplete="username"
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "6px",
                    border: "1px solid var(--line)",
                    background: "var(--bg)",
                    color: "var(--text)",
                    fontSize: "0.9rem",
                    boxSizing: "border-box",
                  }}
                />
              </div>
              <div style={{ marginBottom: "20px" }}>
                <label htmlFor="login-password" style={{ display: "block", marginBottom: "6px", fontSize: "0.875rem", fontWeight: 500 }}>
                  Password
                </label>
                <input
                  id="login-password"
                  type="password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "6px",
                    border: "1px solid var(--line)",
                    background: "var(--bg)",
                    color: "var(--text)",
                    fontSize: "0.9rem",
                    boxSizing: "border-box",
                  }}
                />
              </div>
              {loginError && (
                <div style={{ color: "var(--red, #e53e3e)", marginBottom: "16px", fontSize: "0.875rem" }}>
                  {loginError}
                </div>
              )}
              <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
                <button type="button" className="btn" onClick={() => setLoginOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={loginLoading}>
                  {loginLoading ? "Signing in..." : "Sign in"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
