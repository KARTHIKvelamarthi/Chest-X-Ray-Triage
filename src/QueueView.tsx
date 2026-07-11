import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchQueue, CaseSummary } from "./api";
import { Disclaimer } from "./Disclaimer";
import { sortCases, SortField } from "./sortCases";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

function reviewReasonLabel(c: CaseSummary): string {
  if (c.review_reason === "low_confidence") return "Low confidence";
  if (c.review_reason === "multiple_findings") {
    const count = c.findings ? c.findings.filter((f) => f.score > 0.6).length : 0;
    return `Multiple findings — ${count} elevated`;
  }
  return "Flagged for review";
}

function CaseCard({
  c,
  onClick,
  showReason = false,
}: {
  c: CaseSummary;
  onClick: () => void;
  showReason?: boolean;
}) {
  const isNeedsReview = c.status === "needs_human_review";
  const cardClass = `case-card ${isNeedsReview ? "status-needs-review" : ""} priority-${c.priority.toLowerCase()}`;

  return (
    <div
      className={cardClass}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && onClick()}
      data-testid={`case-card-${c.id}`}
    >
      <div className="case-card-body">
        <div className="case-card-row">
          <strong className="case-finding">{c.top_finding}</strong>
          <span className="confidence-badge">{(c.top_score * 100).toFixed(0)}%</span>
        </div>
        <div className="case-card-row">
          <span className={`badge badge-priority-${c.priority.toLowerCase()}`}>
            {c.priority}
          </span>
          <span className="case-time">{new Date(c.created_at).toLocaleDateString()}</span>
        </div>
        {showReason && c.review_reason && (
          <p className="review-reason-label" data-testid={`review-reason-${c.id}`}>
            {reviewReasonLabel(c)}
          </p>
        )}
        <p className="case-filename">{c.filename}</p>
      </div>
    </div>
  );
}

export function QueueView() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<SortField>("priority");
  const [filter, setFilter] = useState<"active" | "needs_review" | "high_priority" | "reviewed">("active");
  const navigate = useNavigate();

  useEffect(() => {
    fetchQueue()
      .then(setCases)
      .catch(() => setError("Failed to load queue."))
      .finally(() => setLoading(false));
  }, []);

  // Calculate totals
  const totalQueueCount = cases.filter((c) => c.status === "pending" || c.status === "needs_human_review").length;
  const needsReviewCount = cases.filter((c) => c.status === "needs_human_review").length;
  const highPriorityCount = cases.filter((c) => c.priority === "High" && c.status !== "reviewed").length;
  const reviewedCount = cases.filter((c) => c.status === "reviewed").length;

  // Filter the cases to display
  let displayNeedsReview = cases.filter((c) => c.status === "needs_human_review");
  let displayRoutine = cases.filter((c) => c.status === "pending");

  if (filter === "needs_review") {
    displayRoutine = [];
  } else if (filter === "high_priority") {
    displayNeedsReview = displayNeedsReview.filter((c) => c.priority === "High");
    displayRoutine = displayRoutine.filter((c) => c.priority === "High");
  } else if (filter === "reviewed") {
    displayNeedsReview = [];
    displayRoutine = cases.filter((c) => c.status === "reviewed");
  }

  const sortedRoutine = sortCases(displayRoutine, sortBy);

  const lowConfCount = displayNeedsReview.filter((c) => c.review_reason === "low_confidence").length;
  const multCount = displayNeedsReview.filter((c) => c.review_reason === "multiple_findings").length;
  const parts = [];
  if (lowConfCount > 0) parts.push(`${lowConfCount} low confidence`);
  if (multCount > 0) parts.push(`${multCount} multiple findings`);
  const laneSubtitle = parts.length > 0
    ? `Requires manual evaluation: ${parts.join(" and ")}.`
    : "These cases have ambiguous or low-confidence findings and require manual evaluation.";

  const routineTitle = filter === "reviewed" ? "Reviewed Cases" : filter === "high_priority" ? "Pending Cases (High Priority)" : "Pending Cases";
  const routineIcon = filter === "reviewed" ? "✓" : "☰";
  const needsReviewTitle = filter === "high_priority" ? "Needs Human Review (High Priority)" : "Needs Human Review";

  return (
    <div className="view-container">
      <Disclaimer />
      <div className="queue-header">
        <h1>Triage Queue</h1>
        <button className="btn-primary" onClick={() => navigate("/")}>
          + New Upload
        </button>
      </div>

      {loading && <p>Loading queue…</p>}
      {error && <p className="inline-error">{error}</p>}

      {/* Summary Stats Row */}
      {!loading && !error && (
        <div className="stats-row">
          <div
            className={`stat-card clickable ${filter === "active" ? "active-filter" : ""}`}
            onClick={() => setFilter("active")}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && setFilter("active")}
            data-testid="stat-total-queue"
          >
            <span className="stat-value">{totalQueueCount}</span>
            <span className="stat-label">Total Queue</span>
          </div>
          <div
            className={`stat-card clickable stat-needs-review ${filter === "needs_review" ? "active-filter" : ""}`}
            onClick={() => setFilter("needs_review")}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && setFilter("needs_review")}
            data-testid="stat-needs-review"
          >
            <span className="stat-value">{needsReviewCount}</span>
            <span className="stat-label">Needs Review</span>
          </div>
          <div
            className={`stat-card clickable stat-high-priority ${filter === "high_priority" ? "active-filter" : ""}`}
            onClick={() => setFilter("high_priority")}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && setFilter("high_priority")}
            data-testid="stat-high-priority"
          >
            <span className="stat-value">{highPriorityCount}</span>
            <span className="stat-label">High Priority</span>
          </div>
          <div
            className={`stat-card clickable stat-reviewed ${filter === "reviewed" ? "active-filter" : ""}`}
            onClick={() => setFilter("reviewed")}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && setFilter("reviewed")}
            data-testid="stat-reviewed"
          >
            <span className="stat-value">{reviewedCount}</span>
            <span className="stat-label">Reviewed</span>
          </div>
        </div>
      )}

      {/* Needs Human Review section */}
      {!loading && filter !== "reviewed" && (
        <section className="queue-lane">
          <h2 className="lane-title subordinate-header">
            <span className="header-icon-prefix">⚠</span> {needsReviewTitle}
          </h2>
          {displayNeedsReview.length === 0 ? (
            <p className="quiet-empty-message">✓ No cases currently require manual review.</p>
          ) : (
            <div className="lane-review" data-testid="needs-review-lane">
              <p className="lane-subtitle">
                {laneSubtitle}
              </p>
              <div className="case-list">
                {displayNeedsReview.map((c) => (
                  <CaseCard key={c.id} c={c} onClick={() => navigate(`/result/${c.id}`)} showReason={true} />
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {/* Routine priority lane */}
      {!loading && (
        <section className="queue-lane" data-testid="routine-lane">
          <div className="lane-header">
            <h2 className="lane-title subordinate-header">
              <span className="header-icon-prefix">{routineIcon}</span> {routineTitle}
            </h2>
            {filter !== "reviewed" && (
              <div className="sort-controls">
                <span>Sort by:</span>
                <button
                  className={`btn-toggle ${sortBy === "priority" ? "active" : ""}`}
                  onClick={() => setSortBy("priority")}
                >
                  Priority
                </button>
                <button
                  className={`btn-toggle ${sortBy === "timestamp" ? "active" : ""}`}
                  onClick={() => setSortBy("timestamp")}
                >
                  Time
                </button>
              </div>
            )}
          </div>

          {sortedRoutine.length === 0 ? (
            <p className="quiet-empty-message">✓ No cases to display.</p>
          ) : (
            <div className="case-list">
              {sortedRoutine.map((c) => (
                <CaseCard key={c.id} c={c} onClick={() => navigate(`/result/${c.id}`)} />
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
