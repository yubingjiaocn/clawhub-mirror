import { useState } from "react";

type Tab = "install" | "publish" | "search" | "setup";

export function InstallCommand({ slug = "example-skill" }: { slug?: string }) {
  const [tab, setTab] = useState<Tab>("install");
  const siteUrl = window.location.origin;

  const commands: Record<Tab, string> = {
    install: `clawhub install ${slug}`,
    publish: `clawhub publish . --slug ${slug} --version 1.0.0`,
    search: `clawhub search "${slug}"`,
    setup: `export CLAWHUB_SITE=${siteUrl}`,
  };

  const tabs: Array<{ id: Tab; label: string }> = [
    { id: "install", label: "Install" },
    { id: "publish", label: "Publish" },
    { id: "search", label: "Search" },
    { id: "setup", label: "Setup" },
  ];

  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(commands[tab]);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="install-switcher">
      <div className="install-switcher-row">
        <div className="stat">Use the clawhub CLI:</div>
        <div className="install-switcher-toggle" role="tablist">
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              className={`install-switcher-pill ${tab === t.id ? "is-active" : ""}`}
              role="tab"
              aria-selected={tab === t.id}
              onClick={() => setTab(t.id)}
            >
              {t.label}
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
          {commands[tab]}
        </pre>
        <span style={{ fontSize: "0.75rem", opacity: 0.6, flexShrink: 0 }}>
          {copied ? "Copied!" : "Copy"}
        </span>
      </div>
    </div>
  );
}
