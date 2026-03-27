export function Footer() {
  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <div className="site-footer-divider" aria-hidden="true" />
        <div className="site-footer-row">
          <div className="site-footer-copy">
            ClawHub Mirror &middot; A self-hosted{" "}
            <a href="https://github.com/openclaw/clawhub" target="_blank" rel="noreferrer">ClawHub</a>{" "}
            registry &middot;{" "}
            <a href="/guide">Guide</a> &middot;{" "}
            <a href="/api">API Reference</a> &middot;{" "}
            <a href="https://docs.openclaw.ai/tools/clawhub" target="_blank" rel="noreferrer">CLI Docs</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
