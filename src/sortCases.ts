import { CaseSummary } from "./api";

export type SortField = "priority" | "timestamp";

export function sortCases(cases: CaseSummary[], by: SortField): CaseSummary[] {
  return [...cases].sort((a, b) => {
    if (by === "priority") {
      const pa = a.priority === "High" ? 0 : 1;
      const pb = b.priority === "High" ? 0 : 1;
      if (pa !== pb) return pa - pb;
      return a.created_at.localeCompare(b.created_at);
    }
    // timestamp ascending
    return a.created_at.localeCompare(b.created_at);
  });
}
