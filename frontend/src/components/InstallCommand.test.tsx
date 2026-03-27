import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { InstallCommand } from "./InstallCommand";

describe("InstallCommand", () => {
  it("renders default install command with slug", () => {
    render(<InstallCommand slug="my-skill" />);
    expect(screen.getByText(/clawhub install my-skill/)).toBeInTheDocument();
  });

  it("renders default slug when none provided", () => {
    render(<InstallCommand />);
    expect(screen.getByText(/example-skill/)).toBeInTheDocument();
  });

  it("switches CLI between clawhub and openclaw", async () => {
    const user = userEvent.setup();
    render(<InstallCommand slug="test" />);

    // Default is clawhub
    expect(screen.getByText(/clawhub install test/)).toBeInTheDocument();

    // Switch to openclaw
    await user.click(screen.getByRole("tab", { name: /openclaw/i }));
    expect(screen.getByText(/openclaw skills install test/)).toBeInTheDocument();
  });

  it("switches between action tabs", async () => {
    const user = userEvent.setup();
    render(<InstallCommand slug="my-skill" />);

    // Click Search tab
    await user.click(screen.getByRole("tab", { name: "Search" }));
    expect(screen.getByText(/clawhub search/)).toBeInTheDocument();

    // Click Publish tab
    await user.click(screen.getByRole("tab", { name: "Publish" }));
    expect(screen.getByText(/clawhub publish/)).toBeInTheDocument();

    // Click Update tab
    await user.click(screen.getByRole("tab", { name: "Update" }));
    expect(screen.getByText(/clawhub update/)).toBeInTheDocument();
  });

  it("shows all four action tabs", () => {
    render(<InstallCommand slug="test" />);
    expect(screen.getByRole("tab", { name: "Install" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Search" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Publish" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Update" })).toBeInTheDocument();
  });
});
