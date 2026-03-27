import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SkillStatLine } from "./SkillStats";

describe("SkillStatLine", () => {
  it("renders small numbers as-is", () => {
    render(<SkillStatLine stars={42} downloads={100} />);
    expect(screen.getByText(/42/)).toBeInTheDocument();
    expect(screen.getByText(/100/)).toBeInTheDocument();
  });

  it("formats thousands with K suffix", () => {
    render(<SkillStatLine stars={1500} downloads={25000} />);
    expect(screen.getByText(/1.5K/)).toBeInTheDocument();
    expect(screen.getByText(/25.0K/)).toBeInTheDocument();
  });

  it("formats millions with M suffix", () => {
    render(<SkillStatLine stars={2500000} downloads={1000000} />);
    expect(screen.getByText(/2.5M/)).toBeInTheDocument();
    expect(screen.getByText(/1.0M/)).toBeInTheDocument();
  });

  it("renders zero values", () => {
    render(<SkillStatLine stars={0} downloads={0} />);
    const text = screen.getByText(/★/).textContent;
    expect(text).toContain("0");
  });
});
