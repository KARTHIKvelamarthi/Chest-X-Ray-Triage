import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { fetchCase, markReviewed, CaseDetail } from "./api";
import { Disclaimer } from "./Disclaimer";

export function ResultView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [reviewing, setReviewing] = useState(false);

  useEffect(() => {
    if (!id) return;
    fetchCase(parseInt(id, 10))
      .then(setCaseData)
      .catch((err) => {
        setError(err.message === "NOT_FOUND" ? "Case not found." : "Failed to load case.");
      });
  }, [id]);

  async function onMarkReviewed() {
    if (!caseData) return;
    setReviewing(true);
    try {
      const updated = await markReviewed(caseData.id);
      setCaseData(updated);
    } catch {
      setError("Failed to mark as reviewed.");
    } finally {
      setReviewing(false);
    }
  }

  const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

  if (error) {
    return (
      <div className="view-container">
        <Disclaimer />
        <p className="inline-error" data-testid="case-not-found">{error}</p>
        <button className="btn-secondary" onClick={() => navigate("/")}>Back</button>
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="view-container">
        <Disclaimer />
        <p>Loading...</p>
      </div>
    );
  }

  const chartData = caseData.findings.slice(0, 10).map((f) => ({
    name: f.label.length > 20 ? f.label.slice(0, 20) + "…" : f.label,
    score: parseFloat((f.score * 100).toFixed(1)),
  }));

  const imgSrc = showHeatmap
    ? `${BASE}${caseData.heatmap_url}`
    : `${BASE}${caseData.thumbnail_url}`;

  return (
    <div className="view-container">
      <Disclaimer />
      <div className="result-header">
        <button className="btn-secondary" onClick={() => navigate("/queue")}>
          ← Queue
        </button>
        <h2>{caseData.filename}</h2>
        {caseData.status === "pending" || caseData.status === "needs_human_review" ? (
          <button
            className="btn-primary"
            onClick={onMarkReviewed}
            disabled={reviewing}
            data-testid="mark-reviewed-btn"
          >
            {reviewing ? "Saving…" : "Mark Reviewed"}
          </button>
        ) : (
          <span className="badge badge-reviewed">Reviewed</span>
        )}
      </div>

      {/* Status badges */}
      <div className="badge-row">
        <span className={`badge badge-priority-${caseData.priority.toLowerCase()}`}>
          {caseData.priority}
        </span>
        {caseData.status === "needs_human_review" && (
          <span className="badge badge-review-needed">⚠ Needs Human Review</span>
        )}
      </div>

      {/* Image / heatmap toggle */}
      <div className="image-section">
        <img
          src={imgSrc}
          alt={showHeatmap ? "Grad-CAM heatmap overlay" : "Original X-ray"}
          className="result-img"
          data-testid="result-image"
        />
        <div className="toggle-row">
          <button
            className={`btn-toggle ${!showHeatmap ? "active" : ""}`}
            onClick={() => setShowHeatmap(false)}
            data-testid="toggle-original"
          >
            Original
          </button>
          <button
            className={`btn-toggle ${showHeatmap ? "active" : ""}`}
            onClick={() => setShowHeatmap(true)}
            data-testid="toggle-heatmap"
          >
            Heatmap
          </button>
        </div>
      </div>

      {/* Custom Finding scores list */}
      <div className="chart-section">
        <h3>Finding Scores (top 10)</h3>
        <div className="chart-list">
          {chartData.map((entry, i) => {
            const levelClass = entry.score > 70 ? "high" : entry.score > 40 ? "medium" : "low";
            return (
              <div
                key={i}
                className={`chart-row ${levelClass}`}
                style={{ "--target-width": `${entry.score}%` } as React.CSSProperties}
              >
                <span className="finding-name" title={entry.name}>
                  {entry.name}
                </span>
                <div className="bar-track">
                  <div className="bar-fill" />
                </div>
                <span className="finding-score">{entry.score}%</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Similar cases panel */}
      <div className="similar-cases-section" data-testid="similar-cases-panel">
        <h3>Similar Historical Cases</h3>
        {caseData.similar_cases.length === 0 ? (
          <p className="empty-state">
            No similar cases found. Run <code>scripts/build_index.py</code> to enable retrieval.
          </p>
        ) : (
          <ul className="similar-cases-list">
            {caseData.similar_cases.map((sc, i) => (
              <li key={i} className="similar-case-card">
                <div className="similar-case-header">
                  <strong>Case {sc.uid}</strong>
                  <span className="similarity-badge">
                    {(sc.similarity * 100).toFixed(1)}% similar
                  </span>
                </div>
                {sc.findings && <p className="report-text"><em>Findings:</em> {sc.findings}</p>}
                {sc.impression && <p className="report-text"><em>Impression:</em> {sc.impression}</p>}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Grounded explanation */}
      <div className="explanation-section">
        <h3>Grounded Explanation</h3>
        <p
          className="disclaimer-label"
          data-testid="explanation-disclaimer"
        >
          AI-generated prototype output — not for clinical use
        </p>
        <p data-testid="explanation-text">{caseData.explanation}</p>
      </div>
    </div>
  );
}
