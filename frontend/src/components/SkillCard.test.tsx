import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SkillCard } from "./SkillCard";
import type { SkillListItem } from "../lib/api";

const baseSkill: SkillListItem = {
  slug: "my-skill",
  displayName: "My Skill",
  summary: "A test skill",
  tags: ["test"],
  stats: { downloads: 42, stars: 5 },
  createdAt: 1700000000000,
  updatedAt: 1700000000000,
  latestVersion: { version: "1.0.0", createdAt: 1700000000000, changelog: null },
};

function renderCard(skill = baseSkill, badge?: string | string[]) {
  return render(
    <MemoryRouter>
      <SkillCard skill={skill} badge={badge} />
    </MemoryRouter>,
  );
}

describe("SkillCard", () => {
  it("renders skill name and summary", () => {
    renderCard();
    expect(screen.getByText("My Skill")).toBeInTheDocument();
    expect(screen.getByText("A test skill")).toBeInTheDocument();
  });

  it("renders default summary when none provided", () => {
    renderCard({ ...baseSkill, summary: null });
    expect(screen.getByText("A fresh skill bundle.")).toBeInTheDocument();
  });

  it("links to skill detail page", () => {
    renderCard();
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/skills/my-skill");
  });

  it("renders stats", () => {
    renderCard();
    expect(screen.getByText(/5/)).toBeInTheDocument();
    expect(screen.getByText(/42/)).toBeInTheDocument();
  });

  it("renders string badge", () => {
    renderCard(baseSkill, "featured");
    expect(screen.getByText("featured")).toBeInTheDocument();
  });

  it("renders array of badges", () => {
    renderCard(baseSkill, ["new", "popular"]);
    expect(screen.getByText("new")).toBeInTheDocument();
    expect(screen.getByText("popular")).toBeInTheDocument();
  });

  it("renders no badges when not provided", () => {
    const { container } = renderCard();
    expect(container.querySelector(".skill-card-tags")).toBeNull();
  });
});
