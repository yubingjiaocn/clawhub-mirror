import { describe, it, expect, beforeEach } from "vitest";
import { getStoredTheme, resolveTheme, applyTheme } from "./theme";

beforeEach(() => {
  localStorage.clear();
  document.documentElement.dataset.theme = "";
  document.documentElement.classList.remove("dark");
});

describe("getStoredTheme", () => {
  it("returns 'system' by default", () => {
    expect(getStoredTheme()).toBe("system");
  });

  it("returns stored value when valid", () => {
    localStorage.setItem("clawhub-theme", "dark");
    expect(getStoredTheme()).toBe("dark");
  });

  it("returns 'system' for invalid stored value", () => {
    localStorage.setItem("clawhub-theme", "invalid");
    expect(getStoredTheme()).toBe("system");
  });
});

describe("resolveTheme", () => {
  it("returns 'light' or 'dark' for system mode", () => {
    const result = resolveTheme("system");
    expect(["light", "dark"]).toContain(result);
  });

  it("returns 'light' for light mode", () => {
    expect(resolveTheme("light")).toBe("light");
  });

  it("returns 'dark' for dark mode", () => {
    expect(resolveTheme("dark")).toBe("dark");
  });
});

describe("applyTheme", () => {
  it("sets data-theme attribute on html element", () => {
    applyTheme("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("adds dark class for dark mode", () => {
    applyTheme("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("removes dark class for light mode", () => {
    document.documentElement.classList.add("dark");
    applyTheme("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("persists to localStorage", () => {
    applyTheme("dark");
    expect(localStorage.getItem("clawhub-theme")).toBe("dark");
  });
});
