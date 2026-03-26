import { useMemo, useState } from "react";

type PackageManager = "npm" | "pnpm" | "bun";

const PACKAGE_MANAGERS: Array<{ id: PackageManager; label: string }> = [
  { id: "npm", label: "npm" },
  { id: "pnpm", label: "pnpm" },
  { id: "bun", label: "bun" },
];

export function InstallCommand({ slug = "example-skill" }: { slug?: string }) {
  const [pm, setPm] = useState<PackageManager>("npm");

  const command = useMemo(() => {
    switch (pm) {
      case "npm": return `npx clawhub@latest install ${slug}`;
      case "pnpm": return `pnpm dlx clawhub@latest install ${slug}`;
      case "bun": return `bunx clawhub@latest install ${slug}`;
    }
  }, [slug, pm]);

  return (
    <div className="install-switcher">
      <div className="install-switcher-row">
        <div className="stat">Install any skill folder in one shot:</div>
        <div className="install-switcher-toggle" role="tablist">
          {PACKAGE_MANAGERS.map(entry => (
            <button
              key={entry.id}
              type="button"
              className={pm === entry.id ? "install-switcher-pill is-active" : "install-switcher-pill"}
              role="tab"
              aria-selected={pm === entry.id}
              onClick={() => setPm(entry.id)}
            >
              {entry.label}
            </button>
          ))}
        </div>
      </div>
      <div className="hero-install-code mono">{command}</div>
    </div>
  );
}
