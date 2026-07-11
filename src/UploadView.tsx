import { useRef, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { analyzeImage } from "./api";
import { Disclaimer } from "./Disclaimer";

const ALLOWED_TYPES = new Set(["image/jpeg", "image/png", "image/jpg"]);

export function UploadView() {
  const [preview, setPreview] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [isWindowDragging, setIsWindowDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  function handleFile(f: File) {
    if (!ALLOWED_TYPES.has(f.type)) {
      setError("Invalid file type. Please upload a JPG or PNG image.");
      setFile(null);
      setPreview(null);
      return;
    }
    setError(null);
    setFile(f);
    setPreview(URL.createObjectURL(f));
  }

  function onInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) handleFile(f);
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) handleFile(f);
  }

  useEffect(() => {
    let dragCounter = 0;

    const handleDragEnter = (e: DragEvent) => {
      e.preventDefault();
      if (e.dataTransfer?.types.includes("Files")) {
        dragCounter++;
        setIsWindowDragging(true);
      }
    };

    const handleDragLeave = (e: DragEvent) => {
      e.preventDefault();
      if (e.dataTransfer?.types.includes("Files")) {
        dragCounter--;
        if (dragCounter === 0) {
          setIsWindowDragging(false);
        }
      }
    };

    const handleDragOver = (e: DragEvent) => {
      e.preventDefault();
    };

    const handleDrop = (e: DragEvent) => {
      e.preventDefault();
      dragCounter = 0;
      setIsWindowDragging(false);
      const f = e.dataTransfer?.files?.[0];
      if (f) {
        handleFile(f);
      }
    };

    window.addEventListener("dragenter", handleDragEnter);
    window.addEventListener("dragleave", handleDragLeave);
    window.addEventListener("dragover", handleDragOver);
    window.addEventListener("drop", handleDrop);

    return () => {
      window.removeEventListener("dragenter", handleDragEnter);
      window.removeEventListener("dragleave", handleDragLeave);
      window.removeEventListener("dragover", handleDragOver);
      window.removeEventListener("drop", handleDrop);
    };
  }, []);

  async function onAnalyze() {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeImage(file);
      navigate(`/result/${result.id}`);
    } catch (err: any) {
      setError(err.message ?? "Analysis failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="view-container">
      <Disclaimer />
      <h1>Chest X-Ray Triage</h1>
      <p className="subtitle">Upload a chest X-ray to run automated analysis.</p>

      {/* Full-screen drag-and-drop visual overlay */}
      {isWindowDragging && (
        <div className="full-screen-drag-overlay">
          <div className="overlay-content">
            <span className="overlay-icon">🫁</span>
            <h2>Drop Chest X-Ray Here</h2>
            <p>Release to instantly stage the image</p>
          </div>
        </div>
      )}

      <div
        className={`drop-zone ${dragging ? "dragging" : ""}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        role="button"
        aria-label="Upload chest X-ray image"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
      >
        {preview ? (
          <div className="preview-container" onClick={(e) => e.stopPropagation()}>
            <img src={preview} alt="Selected X-ray preview" className="preview-img" />
            <div className="file-details-card">
              <span className="file-details-icon">📄</span>
              <div className="file-details-info">
                <p className="file-details-name" title={file?.name}>{file?.name}</p>
                <p className="file-details-size">
                  {file ? (file.size / 1024 / 1024).toFixed(2) : "0.00"} MB
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className="drop-placeholder">
            <span className="drop-icon">🫁</span>
            <p>Drag &amp; drop or click to select a JPG/PNG</p>
          </div>
        )}
        <input
          ref={inputRef}
          type="file"
          accept=".jpg,.jpeg,.png"
          onChange={onInputChange}
          style={{ display: "none" }}
          data-testid="file-input"
        />
      </div>

      {error && (
        <p className="inline-error" role="alert" data-testid="upload-error">
          {error}
        </p>
      )}

      <div className="button-row">
        <button
          className="btn-primary"
          onClick={onAnalyze}
          disabled={!file || loading}
          aria-busy={loading}
        >
          {loading ? <span className="spinner" aria-label="Analyzing..." /> : "Analyze"}
        </button>
        {file && !loading && (
          <button
            className="btn-secondary"
            onClick={() => {
              setFile(null);
              setPreview(null);
              setError(null);
            }}
          >
            Clear Selection
          </button>
        )}
        <button className="btn-secondary" onClick={() => navigate("/queue")}>
          View Queue
        </button>
      </div>
    </div>
  );
}
