/**
 * Feature: chest-xray-triage, Property 11: Client-side sort produces a correctly ordered list
 */
import { describe, it, expect } from "vitest";
import fc from "fast-check";
import { sortCases } from "../sortCases";
import type { CaseSummary } from "../api";

function makeCase(overrides: Partial<CaseSummary> = {}): CaseSummary {
  return {
    id: Math.floor(Math.random() * 10000),
    filename: "test.png",
    top_finding: "Pneumonia",
    top_score: 0.5,
    thumbnail_url: "",
    priority: "Normal",
    status: "pending",
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

const caseArbitrary = fc.record({
  id: fc.integer({ min: 1, max: 100000 }),
  filename: fc.string({ minLength: 1, maxLength: 30 }),
  top_finding: fc.string({ minLength: 1, maxLength: 30 }),
  top_score: fc.float({ min: 0, max: 1, noNaN: true }),
  thumbnail_url: fc.constant(""),
  priority: fc.oneof(fc.constant("High"), fc.constant("Normal")),
  status: fc.oneof(
    fc.constant("pending"),
    fc.constant("reviewed"),
    fc.constant("needs_human_review")
  ),
  created_at: fc
    .date({ min: new Date("2020-01-01"), max: new Date("2030-01-01") })
    .map((d) => d.toISOString()),
});

describe("sortCases — Property 11", () => {
  it("priority sort: all High before all Normal (100 runs)", () => {
    fc.assert(
      fc.property(fc.array(caseArbitrary, { minLength: 0, maxLength: 50 }), (cases) => {
        const sorted = sortCases(cases, "priority");
        let seenNormal = false;
        for (const c of sorted) {
          if (c.priority === "Normal") seenNormal = true;
          if (seenNormal && c.priority === "High") return false;
        }
        return true;
      }),
      { numRuns: 100 }
    );
  });

  it("timestamp sort: ascending created_at (100 runs)", () => {
    fc.assert(
      fc.property(fc.array(caseArbitrary, { minLength: 0, maxLength: 50 }), (cases) => {
        const sorted = sortCases(cases, "timestamp");
        for (let i = 1; i < sorted.length; i++) {
          if (sorted[i].created_at < sorted[i - 1].created_at) return false;
        }
        return true;
      }),
      { numRuns: 100 }
    );
  });

  it("empty array returns empty", () => {
    expect(sortCases([], "priority")).toEqual([]);
    expect(sortCases([], "timestamp")).toEqual([]);
  });

  it("does not mutate the original array", () => {
    const original = [makeCase({ priority: "Normal" }), makeCase({ priority: "High" })];
    const sorted = sortCases(original, "priority");
    expect(original[0].priority).toBe("Normal"); // unchanged
    expect(sorted[0].priority).toBe("High");
  });
});
