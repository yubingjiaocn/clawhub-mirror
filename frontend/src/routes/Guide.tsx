export function Guide() {
  const siteUrl = window.location.origin;
  const registryUrl = `${siteUrl}/api/v1`;

  const codeBlock = (code: string) => (
    <pre
      style={{
        background: "var(--surface)",
        border: "1px solid var(--line)",
        borderRadius: "8px",
        padding: "12px 16px",
        overflowX: "auto",
        fontSize: "0.85rem",
        lineHeight: 1.5,
        cursor: "pointer",
        position: "relative",
      }}
      onClick={() => navigator.clipboard.writeText(code)}
      title="Click to copy"
    >
      <code>{code}</code>
    </pre>
  );

  return (
    <main className="section" style={{ maxWidth: "760px", margin: "0 auto", padding: "48px 24px" }}>
      <h1 style={{ fontSize: "1.75rem", marginBottom: "8px" }}>Getting Started</h1>
      <p style={{ color: "var(--muted)", marginBottom: "40px" }}>
        How to install, search, publish, and manage AgentSkills with this private registry.
      </p>

      {/* --- Quick Setup --- */}
      <section style={{ marginBottom: "40px" }}>
        <h2 style={{ fontSize: "1.25rem", marginBottom: "16px" }}>1. Install the CLI</h2>
        <p style={{ marginBottom: "12px" }}>
          Install the{" "}
          <a href="https://docs.openclaw.ai/tools/clawhub" target="_blank" rel="noreferrer">clawhub CLI</a>{" "}
          globally:
        </p>
        {codeBlock("npm i -g clawhub")}
        <p style={{ marginBottom: "12px", marginTop: "12px", color: "var(--muted)", fontSize: "0.9rem" }}>
          Or use <code>pnpm add -g clawhub</code>. The{" "}
          <a href="https://docs.openclaw.ai/cli#skills" target="_blank" rel="noreferrer">openclaw skills</a>{" "}
          subcommands also work.
        </p>
      </section>

      {/* --- Authentication --- */}
      <section style={{ marginBottom: "40px" }}>
        <h2 style={{ fontSize: "1.25rem", marginBottom: "16px" }}>2. Authenticate</h2>

        <h3 style={{ fontSize: "1rem", marginBottom: "8px", fontWeight: 600 }}>Option A: Sign up on the web</h3>
        <p style={{ marginBottom: "16px" }}>
          Click <strong>Sign in</strong> in the header, then <strong>Sign up</strong> to create an account.
          Go to <strong>Settings</strong> to generate an API key for CLI use.
        </p>

        <h3 style={{ fontSize: "1rem", marginBottom: "8px", fontWeight: 600 }}>Option B: Login with the CLI</h3>
        <p style={{ marginBottom: "8px" }}>If an admin has created your account:</p>
        {codeBlock(`CLAWHUB_SITE=${siteUrl} clawhub login --token <your-api-key>`)}

        <p style={{ marginBottom: "8px", marginTop: "16px" }}>Verify your identity:</p>
        {codeBlock(`CLAWHUB_SITE=${siteUrl} clawhub whoami`)}
      </section>

      {/* --- Environment Variables --- */}
      <section style={{ marginBottom: "40px" }}>
        <h2 style={{ fontSize: "1.25rem", marginBottom: "16px" }}>3. Configure your environment</h2>
        <p style={{ marginBottom: "12px" }}>
          Set these environment variables to avoid passing them on every command:
        </p>

        <div style={{
          background: "var(--surface)",
          border: "1px solid var(--line)",
          borderRadius: "8px",
          overflow: "hidden",
          marginBottom: "12px",
        }}>
          <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--line)" }}>
            <strong style={{ fontSize: "0.9rem" }}>For clawhub CLI</strong>
          </div>
          <pre style={{ padding: "12px 16px", margin: 0, fontSize: "0.85rem", overflowX: "auto", cursor: "pointer" }}
            onClick={() => navigator.clipboard.writeText(`export CLAWHUB_SITE=${siteUrl}`)}
            title="Click to copy"
          >
            <code>{`# Add to your shell profile (.bashrc, .zshrc, etc.)\nexport CLAWHUB_SITE=${siteUrl}`}</code>
          </pre>
        </div>

        <div style={{
          background: "var(--surface)",
          border: "1px solid var(--line)",
          borderRadius: "8px",
          overflow: "hidden",
        }}>
          <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--line)" }}>
            <strong style={{ fontSize: "0.9rem" }}>For openclaw skills</strong>
          </div>
          <pre style={{ padding: "12px 16px", margin: 0, fontSize: "0.85rem", overflowX: "auto", cursor: "pointer" }}
            onClick={() => navigator.clipboard.writeText(`export CLAWHUB_REGISTRY=${registryUrl}`)}
            title="Click to copy"
          >
            <code>{`# Add to your shell profile (.bashrc, .zshrc, etc.)\nexport CLAWHUB_REGISTRY=${registryUrl}`}</code>
          </pre>
        </div>

        <table style={{ width: "100%", marginTop: "16px", fontSize: "0.85rem", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid var(--line)" }}>
              <th style={{ padding: "8px 0" }}>Variable</th>
              <th style={{ padding: "8px 0" }}>Used by</th>
              <th style={{ padding: "8px 0" }}>Description</th>
            </tr>
          </thead>
          <tbody>
            <tr style={{ borderBottom: "1px solid var(--line)" }}>
              <td style={{ padding: "8px 0" }}><code>CLAWHUB_SITE</code></td>
              <td style={{ padding: "8px 0" }}>clawhub CLI</td>
              <td style={{ padding: "8px 0" }}>Site URL. CLI fetches <code>/.well-known/clawhub.json</code> to discover the API.</td>
            </tr>
            <tr style={{ borderBottom: "1px solid var(--line)" }}>
              <td style={{ padding: "8px 0" }}><code>CLAWHUB_REGISTRY</code></td>
              <td style={{ padding: "8px 0" }}>openclaw skills</td>
              <td style={{ padding: "8px 0" }}>Direct API base URL. No discovery step.</td>
            </tr>
            <tr>
              <td style={{ padding: "8px 0" }}><code>CLAWHUB_CONFIG_PATH</code></td>
              <td style={{ padding: "8px 0" }}>Both</td>
              <td style={{ padding: "8px 0" }}>Override token/config storage location.</td>
            </tr>
          </tbody>
        </table>
      </section>

      {/* --- Search & Install --- */}
      <section style={{ marginBottom: "40px" }}>
        <h2 style={{ fontSize: "1.25rem", marginBottom: "16px" }}>4. Search and install skills</h2>

        <p style={{ marginBottom: "8px" }}>Search for skills:</p>
        {codeBlock("clawhub search \"git\"")}

        <p style={{ marginBottom: "8px", marginTop: "16px" }}>Install a skill into your project:</p>
        {codeBlock("clawhub install git-essentials")}

        <p style={{ marginBottom: "8px", marginTop: "16px" }}>Install a specific version:</p>
        {codeBlock("clawhub install git-essentials --version 1.0.0")}

        <p style={{ marginBottom: "8px", marginTop: "16px" }}>List installed skills:</p>
        {codeBlock("clawhub list")}

        <p style={{ marginBottom: "8px", marginTop: "16px" }}>Update all installed skills:</p>
        {codeBlock("clawhub update --all")}

        <p style={{ marginBottom: "0", marginTop: "16px", color: "var(--muted)", fontSize: "0.9rem" }}>
          Skills are installed to <code>./skills/&lt;slug&gt;/</code> and tracked in <code>.clawhub/lock.json</code>.
        </p>
      </section>

      {/* --- Publishing --- */}
      <section style={{ marginBottom: "40px" }}>
        <h2 style={{ fontSize: "1.25rem", marginBottom: "16px" }}>5. Publish a skill</h2>
        <p style={{ marginBottom: "12px" }}>
          Create a <code>SKILL.md</code> file with YAML frontmatter in your skill folder:
        </p>
        {codeBlock(`---
name: my-skill
description: A useful agent skill for doing X.
version: 1.0.0
metadata:
  openclaw:
    requires:
      env:
        - MY_API_KEY
      bins:
        - curl
---

# My Skill

Instructions for the agent go here.`)}

        <p style={{ marginBottom: "8px", marginTop: "16px" }}>Publish to this registry:</p>
        {codeBlock("clawhub publish ./my-skill --slug my-skill --version 1.0.0 --tags latest")}

        <p style={{ marginBottom: "8px", marginTop: "16px" }}>Update an existing skill:</p>
        {codeBlock("clawhub publish ./my-skill --slug my-skill --version 1.1.0 --changelog \"Added new feature\"")}

        <p style={{ marginBottom: "8px", marginTop: "16px" }}>Batch publish all skills in a directory:</p>
        {codeBlock("clawhub sync --all")}

        <p style={{ marginBottom: "0", marginTop: "16px", color: "var(--muted)", fontSize: "0.9rem" }}>
          Publishing requires <strong>publisher</strong> or <strong>admin</strong> role.
          New accounts default to <strong>reader</strong>. Ask an admin to upgrade your role.
        </p>
      </section>

      {/* --- API Keys --- */}
      <section style={{ marginBottom: "40px" }}>
        <h2 style={{ fontSize: "1.25rem", marginBottom: "16px" }}>6. API keys</h2>
        <p style={{ marginBottom: "12px" }}>
          API keys are for CLI and programmatic access. Generate them from the{" "}
          <a href="/settings" style={{ textDecoration: "underline" }}>Settings</a> page,
          or via the API:
        </p>
        {codeBlock(`# Login to get a session token
curl -X POST ${siteUrl}/api/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"username": "you", "password": "your-password"}'

# Generate an API key (use the session token)
curl -X POST ${siteUrl}/api/v1/auth/keys \\
  -H "Authorization: Bearer <session-token>" \\
  -H "Content-Type: application/json" \\
  -d '{"label": "my-laptop"}'`)}

        <p style={{ marginBottom: "0", marginTop: "12px", color: "var(--muted)", fontSize: "0.9rem" }}>
          Each user can have up to 10 active API keys. Revoke unused keys from Settings.
        </p>
      </section>

      {/* --- Roles --- */}
      <section style={{ marginBottom: "40px" }}>
        <h2 style={{ fontSize: "1.25rem", marginBottom: "16px" }}>7. User roles</h2>
        <table style={{ width: "100%", fontSize: "0.9rem", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "2px solid var(--line)" }}>
              <th style={{ padding: "8px 0" }}>Role</th>
              <th style={{ padding: "8px 0" }}>Permissions</th>
            </tr>
          </thead>
          <tbody>
            <tr style={{ borderBottom: "1px solid var(--line)" }}>
              <td style={{ padding: "10px 0" }}><strong>reader</strong></td>
              <td style={{ padding: "10px 0" }}>Browse, search, install, download skills. Manage own API keys.</td>
            </tr>
            <tr style={{ borderBottom: "1px solid var(--line)" }}>
              <td style={{ padding: "10px 0" }}><strong>publisher</strong></td>
              <td style={{ padding: "10px 0" }}>Everything readers can do + publish and update skills.</td>
            </tr>
            <tr>
              <td style={{ padding: "10px 0" }}><strong>admin</strong></td>
              <td style={{ padding: "10px 0" }}>Everything + manage users, admission policies, delete skills.</td>
            </tr>
          </tbody>
        </table>
        <p style={{ marginTop: "12px", color: "var(--muted)", fontSize: "0.9rem" }}>
          New accounts created via sign-up get the <strong>reader</strong> role.
          Admins can promote users from the <a href="/admin" style={{ textDecoration: "underline" }}>Admin</a> panel.
        </p>
      </section>

      {/* --- Using with openclaw --- */}
      <section style={{ marginBottom: "40px" }}>
        <h2 style={{ fontSize: "1.25rem", marginBottom: "16px" }}>8. Using with OpenClaw</h2>
        <p style={{ marginBottom: "12px" }}>
          If you use the <a href="https://docs.openclaw.ai/cli#skills" target="_blank" rel="noreferrer">OpenClaw CLI</a>,
          skills are managed via the <code>openclaw skills</code> subcommand:
        </p>
        {codeBlock(`# Set registry (add to shell profile)
export CLAWHUB_REGISTRY=${registryUrl}

# Search
openclaw skills search "git"

# Install
openclaw skills install git-essentials

# Update all
openclaw skills update --all

# List installed
openclaw skills list

# Check readiness (missing env vars, binaries)
openclaw skills check`)}
      </section>

      {/* --- Troubleshooting --- */}
      <section style={{ marginBottom: "20px" }}>
        <h2 style={{ fontSize: "1.25rem", marginBottom: "16px" }}>Troubleshooting</h2>
        <div style={{ display: "grid", gap: "12px" }}>
          <div style={{
            background: "var(--surface)", border: "1px solid var(--line)",
            borderRadius: "8px", padding: "16px",
          }}>
            <strong style={{ fontSize: "0.9rem" }}>CLI says "Not logged in"</strong>
            <p style={{ margin: "8px 0 0", fontSize: "0.85rem", color: "var(--muted)" }}>
              Make sure <code>CLAWHUB_SITE</code> is set and you've run <code>clawhub login --token &lt;key&gt;</code>.
              Generate an API key from the Settings page.
            </p>
          </div>
          <div style={{
            background: "var(--surface)", border: "1px solid var(--line)",
            borderRadius: "8px", padding: "16px",
          }}>
            <strong style={{ fontSize: "0.9rem" }}>Publish returns 403 Forbidden</strong>
            <p style={{ margin: "8px 0 0", fontSize: "0.85rem", color: "var(--muted)" }}>
              Your account needs the <strong>publisher</strong> or <strong>admin</strong> role.
              Ask an admin to upgrade your role.
            </p>
          </div>
          <div style={{
            background: "var(--surface)", border: "1px solid var(--line)",
            borderRadius: "8px", padding: "16px",
          }}>
            <strong style={{ fontSize: "0.9rem" }}>Search returns no results</strong>
            <p style={{ margin: "8px 0 0", fontSize: "0.85rem", color: "var(--muted)" }}>
              This is a private registry. Skills must be published here first.
              They are not mirrored from the public ClawHub registry automatically.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
