import { describe, it, expect } from "vitest";
import { cn } from "./utils";

describe("cn utility", () => {
  it("merges class names correctly", () => {
    expect(cn("px-2", "py-1")).toBe("px-2 py-1");
  });

  it("handles conditional classes", () => {
    const isTrue = true;
    const isFalse = false;
    expect(cn("base", isTrue && "active", isFalse && "inactive")).toBe("base active");
  });

  it("resolves Tailwind conflicts using tailwind-merge", () => {
    expect(cn("px-2 text-sm", "px-4 text-lg")).toBe("px-4 text-lg");
    expect(cn("bg-red-500", "bg-blue-500")).toBe("bg-blue-500");
  });

  it("handles empty or falsy inputs gracefully", () => {
    expect(cn("", null, undefined, false)).toBe("");
  });
});
