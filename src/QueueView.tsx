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
  return (
    <div
      className="case-card"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && onClick()}
      data-testid={`case-card-${c.id}`}
    >
      {c.thumbnail_url && (
        <img
          src={`${BASE}${c.thumbnail_url}`}
          alt={`Thumbnail for ${c.filename}`}
          className="case-thumb"
        />
      )}
      <div className="case-card-body">
        <div className="case-card-row">
          <strong className="case-finding">{c.top_finding}</strong>
          <span className="confidence-badge">{(c.top_score * 100).toFixed(0)}%</span>
        </div>
        <div className="case-card-row">
          <span className={`badge badge-priority-${c.priority.toLowerCase()}`}>
            {c.priority}
          </span>
          <span className="case-time">{new Date(c.created_at).toLocaleString()}</span>
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
  const navigate = useNavigate();

  useEffect(() => {
    fetchQueue()
      .then(setCases)
      .catch(() => setError("Failed to load queue."))
      .finally(() => setLoading(false));
  }, []);

  const needsReview = cases.filter((c) => c.status === "needs_human_review");
  const routine = cases.filter((c) => c.status !== "needs_human_review");
  const sortedRoutine = sortCases(routine, sortBy);

  const lowConfCount = needsReview.filter((c) => c.review_reason === "low_confidence").length;
  const multCount = needsReview.filter((c) => c.review_reason === "multiple_findings").length;
  const parts = [];
  if (lowConfCount > 0) parts.push(`${lowConfCount} low confidence`);
  if (multCount > 0) parts.push(`${multCount} multiple findings`);
  const laneSubtitle = parts.length > 0
    ? `Requires manual evaluation: ${parts.join(" and ")}.`
    : "These cases have ambiguous or low-confidence findings and require manual evaluation.";

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

      {/* Needs Human Review lane */}
      {needsReview.length > 0 && (
        <section className="queue-lane lane-review" data-testid="needs-review-lane">
          <h2 className="lane-title">⚠ Needs Human Review</h2>
          <p className="lane-subtitle">
            {laneSubtitle}
          </p>
          <div className="case-list">
            {needsReview.map((c) => (
              <CaseCard key={c.id} c={c} onClick={() => navigate(`/result/${c.id}`)} showReason={true} />
            ))}
          </div>
        </section>
      )}

      {/* Routine priority lane */}
      <section className="queue-lane" data-testid="routine-lane">
        <div className="lane-header">
          <h2 className="lane-title">Pending Cases</h2>
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
        </div>

        {sortedRoutine.length === 0 && !loading ? (
          <p className="empty-state">No cases in the queue. Upload an X-ray to get started.</p>
        ) : (
          <div className="case-list">
            {sortedRoutine.map((c) => (
              <CaseCard key={c.id} c={c} onClick={() => navigate(`/result/${c.id}`)} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
