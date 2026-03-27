import { useState } from "react";

type Cli = "clawhub" | "openclaw";
type Action = "install" | "search" | "publish" | "update";

export function InstallCommand({ slug = "example-skill" }: { slug?: string }) {
  const [cli, setCli] = useState<Cli>("clawhub");
  const [action, setAction] = useState<Action>("install");
  const siteUrl = window.location.origin;

  const commands: Record<Cli, Record<Action, string>> = {
    clawhub: {
      install: `CLAWHUB_SITE=${siteUrl} clawhub install ${slug}`,
      search: `CLAWHUB_SITE=${siteUrl} clawhub search "${slug}"`,
      publish: `CLAWHUB_SITE=${siteUrl} clawhub publish . --slug ${slug} --version 1.0.0`,
      update: `CLAWHUB_SITE=${siteUrl} clawhub update --all`,
    },
    openclaw: {
      install: `openclaw skills install ${slug}`,
      search: `openclaw skills search "${slug}"`,
      publish: `CLAWHUB_SITE=${siteUrl} clawhub publish . --slug ${slug} --version 1.0.0`,
      update: `openclaw skills update --all`,
    },
  };

  const command = commands[cli][action];

  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(command);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const actions: Array<{ id: Action; label: string }> = [
    { id: "install", label: "Install" },
    { id: "search", label: "Search" },
    { id: "publish", label: "Publish" },
    { id: "update", label: "Update" },
  ];

  return (
    <div className="install-switcher">
      <div className="install-switcher-row" style={{ flexWrap: "wrap", gap: "8px" }}>
        <div className="stat" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          via{" "}
          <div className="install-switcher-toggle" role="tablist" style={{ display: "inline-flex" }}>
            <button
              type="button"
              className={`install-switcher-pill ${cli === "clawhub" ? "is-active" : ""}`}
              role="tab"
              aria-selected={cli === "clawhub"}
              onClick={() => setCli("clawhub")}
            >
              clawhub
            </button>
            <button
              type="button"
              className={`install-switcher-pill ${cli === "openclaw" ? "is-active" : ""}`}
              role="tab"
              aria-selected={cli === "openclaw"}
              onClick={() => setCli("openclaw")}
            >
              openclaw
            </button>
          </div>
        </div>
        <div className="install-switcher-toggle" role="tablist">
          {actions.map((a) => (
            <button
              key={a.id}
              type="button"
              className={`install-switcher-pill ${action === a.id ? "is-active" : ""}`}
              role="tab"
              aria-selected={action === a.id}
              onClick={() => setAction(a.id)}
            >
              {a.label}
            </button>
          ))}
        </div>
      </div>
      <div
        className="hero-install-code mono"
        style={{ display: "flex", alignItems: "flex-start", gap: "8px", cursor: "pointer" }}
        onClick={handleCopy}
        title="Click to copy"
      >
        <pre style={{ margin: 0, flex: 1, whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
          {command}
        </pre>
        <span style={{ fontSize: "0.75rem", opacity: 0.6, flexShrink: 0 }}>
          {copied ? "Copied!" : "Copy"}
        </span>
      </div>
      <div style={{ fontSize: "0.75rem", color: "var(--muted)", marginTop: "8px" }}>
        {cli === "clawhub" ? (
          <>Install CLI: <code>npm i -g clawhub</code> · <a href="https://docs.openclaw.ai/tools/clawhub" target="_blank" rel="noreferrer" style={{ textDecoration: "underline" }}>Docs</a></>
        ) : (
          <>OpenClaw skills subcommand · <a href="https://docs.openclaw.ai/cli#skills" target="_blank" rel="noreferrer" style={{ textDecoration: "underline" }}>Docs</a></>
        )}
      </div>
    </div>
  );
}
