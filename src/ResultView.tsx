import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { fetchCase, markReviewed, deleteCase, CaseDetail } from "./api";
import { Disclaimer } from "./Disclaimer";

export function ResultView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [activeLightboxImage, setActiveLightboxImage] = useState<string | null>(null);

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

  async function onDeleteCase() {
    if (!caseData) return;
    if (!window.confirm("Are you sure you want to permanently delete this case?")) return;
    setDeleting(true);
    try {
      await deleteCase(caseData.id);
      navigate("/queue");
    } catch {
      setError("Failed to delete case.");
      setDeleting(false);
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

  function handleEvidenceClick(uids: string[]) {
    uids.forEach((uid, index) => {
      const el = document.getElementById(`case-${uid}`);
      if (el) {
        if (index === 0) {
          el.scrollIntoView({ behavior: "smooth", block: "center" });
        }
        el.classList.add("highlighted-case");
        setTimeout(() => {
          el.classList.remove("highlighted-case");
        }, 2000);
      }
    });
  }

  function renderExplanation(text: string, evidenceLinks?: Record<string, string[]>) {
    if (!text) return "";
    if (!evidenceLinks) return text;

    const keys = Object.keys(evidenceLinks).filter(
      (k) => evidenceLinks[k] && evidenceLinks[k].length > 0
    );
    if (keys.length === 0) return text;

    // Sort by length desc to match longer labels first
    keys.sort((a, b) => b.length - a.length);

    // Escape keys for RegExp
    const escapedKeys = keys.map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
    const pattern = new RegExp(`\\b(${escapedKeys.join("|")})\\b`, "g");
    const parts = text.split(pattern);

    return parts.map((part, i) => {
      if (keys.includes(part)) {
        return (
          <span
            key={i}
            className="evidence-link-span"
            onClick={() => handleEvidenceClick(evidenceLinks[part])}
          >
            {part}
          </span>
        );
      }
      return part;
    });
  }

  return (
    <div className="view-container result-details-layout">
      <Disclaimer />
      <div className="result-header">
        <button className="btn-secondary" onClick={() => navigate("/queue")}>
          ← Queue
        </button>
        <h2>{caseData.filename}</h2>
        <div className="header-actions">
          {caseData.status === "pending" || caseData.status === "needs_human_review" ? (
            <button
              className="btn-primary"
              onClick={onMarkReviewed}
              disabled={reviewing || deleting}
              data-testid="mark-reviewed-btn"
            >
              {reviewing ? "Saving…" : "Mark Reviewed"}
            </button>
          ) : (
            <span className="badge badge-reviewed">Reviewed</span>
          )}
          <button
            className="btn-danger"
            onClick={onDeleteCase}
            disabled={reviewing || deleting}
            data-testid="delete-case-btn"
          >
            {deleting ? "Deleting…" : "Delete Case"}
          </button>
        </div>
      </div>

      {/* Row 1: Three-column layout */}
      <div className="result-top-section">
        {/* Left Column: Priority tag, X-ray image, and Original/Heatmap toggle */}
        <div className="result-left-column">
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
        </div>

        {/* Right Column: Finding Scores chart with glassmorphism */}
        <div className="result-right-column">
          <div className="chart-section glassmorphic-chart">
            <h3>FINAL SCORES</h3>
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
        </div>

        {/* Column 3: Grounded Explanation sidebar panel */}
        <div className="result-explanation-column">
          <div className="explanation-section sidebar-explanation-panel">
            <h3>Grounded Explanation</h3>
            <div className="sidebar-message-bubble">
              <p
                className="disclaimer-label sidebar-message-header"
                data-testid="explanation-disclaimer"
              >
                AI-generated prototype output — not for clinical use
              </p>
              <div className="sidebar-message-content">
                <p data-testid="explanation-text">
                  {renderExplanation(caseData.explanation, caseData.evidence_links)}
                </p>
              </div>
            </div>
          </div>
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
          <div className="similar-cases-scroll-container">
            <ul className="similar-cases-list">
              {caseData.similar_cases.map((sc, i) => (
                <li key={i} id={`case-${sc.uid}`} className="similar-case-card-new">
                  {sc.image_url && (
                    <img
                      src={`${BASE}${sc.image_url}`}
                      alt={`Case ${sc.uid} X-ray`}
                      className="similar-case-card-thumb"
                      onClick={(e) => {
                        e.stopPropagation();
                        setActiveLightboxImage(`${BASE}${sc.image_url}`);
                      }}
                    />
                  )}
                  <div className="similar-case-card-body">
                    <div className="similar-case-header">
                      <strong>Case {sc.uid}</strong>
                      <span className="similarity-badge">
                        {(sc.similarity * 100).toFixed(1)}%
                      </span>
                    </div>
                    {sc.findings && <p className="report-text"><em>Findings:</em> {sc.findings}</p>}
                    {sc.impression && <p className="report-text"><em>Impression:</em> {sc.impression}</p>}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>



      {/* Lightbox modal overlay */}
      {activeLightboxImage && (
        <div
          className="lightbox-overlay"
          onClick={() => setActiveLightboxImage(null)}
          data-testid="lightbox-overlay"
        >
          <div className="lightbox-content" onClick={(e) => e.stopPropagation()}>
            <button className="lightbox-close" onClick={() => setActiveLightboxImage(null)}>
              &times;
            </button>
            <img src={activeLightboxImage} alt="Fullscreen X-ray" className="lightbox-img" />
          </div>
        </div>
      )}
    </div>
  );
}
