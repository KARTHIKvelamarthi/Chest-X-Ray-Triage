# Implementation Plan: Chest X-Ray Triage

## Overview

Implement the full-stack chest X-ray triage prototype incrementally, starting with the backend core (DB, priority logic, classifier), then building up the pipeline (Grad-CAM, retrieval, explanation), followed by the offline indexer, then the FastAPI routes, and finally the React frontend.

## Tasks

- [x] 1. Project scaffold and SQLite schema
  - Create directory structure: `app/`, `app/routers/`, `scripts/`, `tests/`, `src/`, `src/__tests__/`, `static/heatmaps/`, `static/thumbnails/`, `data/`
  - Create `app/db.py` with `init_db`, `insert_case`, `get_queue`, `get_case`, `update_case_status`
  - Create `app/main.py` with lifespan, `/static` mount, and router registration stubs
  - Create `requirements.txt` (fastapi, uvicorn, torchxrayvision, pytorch-grad-cam, pillow, openai, hypothesis, pytest, pytest-anyio, httpx)
  - Create `package.json` / Vite config for the React frontend with vitest, @testing-library/react, fast-check
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [ ]* 1.1 Write property tests for DB operations (P6, P7, P8)
    - **Property 6: Case persistence round-trip** — insert a case, retrieve by id, assert fields match
    - **Property 7: Queue filter returns only matching-status cases in correct order**
    - **Property 8: Mark-reviewed removes case from pending view**
    - Use in-memory SQLite; generate random case dicts via `hypothesis`
    - _Validates: Requirements 6.1, 6.7, 7.1, 7.2, 7.3_

- [x] 2. Priority and escalation logic
  - Create `app/priority.py` with `compute_priority` and `needs_human_review`
  - `compute_priority`: return `"High"` if any score > 0.7, else `"Normal"`
  - `needs_human_review`: return `True` if top-2 diff ≤ 0.15 OR both top-2 < 0.4
  - _Requirements: 6.2, 6.3_

  - [ ]* 2.1 Write property tests for priority logic (P9, P10)
    - **Property 9: compute_priority assigns High iff any score exceeds 0.7**
    - **Property 10: needs_human_review triggers on ambiguous or low-confidence scores**
    - Use `hypothesis` `st.dictionaries(st.text(min_size=1), st.floats(0.0, 1.0), min_size=2)`
    - Tag each test with `settings(max_examples=100)`
    - _Validates: Requirements 6.2, 6.3_

- [x] 3. Classifier and feature extractor
  - Create `app/classifier.py` with `load_model`, `run_inference`, `get_query_embedding`
  - `load_model`: load `densenet121-res224-all` once, return model in eval mode
  - `run_inference`: preprocess image array via `xrv.datasets.normalize` + `xrv.transforms`, return `{label: score}` for all 18 pathology labels
  - `get_query_embedding`: hook `model.features` output to extract 1024-d vector
  - Load model singleton at startup in `app/main.py` lifespan
  - _Requirements: 2.1, 2.2, 2.3_

  - [ ]* 3.1 Write property test for inference output validity (P1)
    - **Property 1: Inference output validity**
    - Generate random 224×224 float32 grayscale arrays via `hypothesis`; assert keys include `Pneumonia`, `Effusion`, `No Finding` and all values ∈ [0.0, 1.0]
    - Mark model-loading tests `@pytest.mark.slow`
    - _Validates: Requirements 2.1_

- [x] 4. Grad-CAM heatmap generation
  - Create `app/gradcam.py` with `generate_heatmap`
  - Use `pytorch_grad_cam.GradCAM` targeting `model.features` with `ClassifierOutputTarget`
  - Overlay jet colormap at 0.5 alpha onto the original PIL image
  - Save to `static/heatmaps/{uuid}.png`; return relative URL path
  - _Requirements: 3.1, 3.2_

  - [ ]* 4.1 Write property test for heatmap file creation (P3)
    - **Property 3: Heatmap file is created for the top finding**
    - Generate random 224×224 float32 tensors + random scores dicts; assert returned path exists, byte length > 0, PIL can open it
    - _Validates: Requirements 3.1, 3.2_

- [x] 5. Embedding retriever
  - Create `app/retriever.py` with `load_index` and `cosine_search`
  - `load_index`: load `data/embeddings.npz`; return `(embeddings_matrix, metadata_list)`; log warning and return empty if file missing
  - `cosine_search`: normalize vectors, compute dot products, return top-k metadata dicts sorted by similarity descending, each containing `uid`, `findings`, `impression`, `similarity`
  - Handle missing index gracefully (return `[]`)
  - _Requirements: 4.2, 4.3_

  - [ ]* 5.1 Write property test for cosine retrieval (P4)
    - **Property 4: Retrieval returns k sorted results with required fields**
    - Generate random embedding matrices (shape N×1024) and random query vectors; assert `len(result) == min(k, N)`, descending similarity, required fields present, similarity ∈ [-1.0, 1.0]
    - _Validates: Requirements 4.2, 4.3_

- [x] 6. Grounded explanation (Explainer)
  - Create `app/explainer.py` with `build_prompt` and `get_explanation`
  - `build_prompt`: construct prompt embedding retrieved `impression` texts as context; include query finding scores
  - `get_explanation`: call OpenAI `gpt-4o-mini`; on missing key or any exception return fallback string `"Automated explanation unavailable. Please review the finding scores and similar cases directly. Research prototype — not for clinical use."`
  - _Requirements: 5.1, 5.2_

  - [ ]* 6.1 Write property test for prompt completeness (P5)
    - **Property 5: Prompt contains all retrieved report text**
    - Generate lists of similar-case dicts with random `impression` strings; assert every non-null impression appears in `build_prompt` output
    - _Validates: Requirements 5.1_

- [x] 7. Checkpoint — backend core passes all tests
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Offline indexer script
  - Create `scripts/build_index.py`
  - Join `data/indiana_projections.csv` + `data/indiana_reports.csv` on `uid`, filter `projection == "Frontal"`
  - For each row: `PIL.Image.open(path)` (ignore `.dcm` extension), preprocess, call `get_query_embedding`
  - Save `data/embeddings.npz` with `embeddings` (N×1024 float32) and `metadata` (N JSON strings with `uid`, `findings`, `impression`, `image_path`)
  - Print progress every 100 images
  - _Requirements: 4.1, 8.1, 8.2, 8.3_

  - [ ]* 8.1 Write property test for indexer metadata (P12)
    - **Property 12: Indexer output contains findings and impression for every Frontal row**
    - Use a 5-row fixture CSV pair; run indexer logic; assert every metadata entry has `findings` and `impression` drawn from the reports CSV
    - _Validates: Requirements 8.1, 8.3_

- [x] 9. FastAPI analyze route
  - Create `app/routers/analyze.py` with `POST /api/analyze`
  - Validate MIME type (image/jpeg or image/png); return 422 on invalid or undecodable image
  - Reject files > 10 MB with HTTP 413
  - Orchestrate: preprocess → `run_inference` → `get_query_embedding` → `generate_heatmap` → save thumbnail → `cosine_search` → `get_explanation` → `compute_priority` + `needs_human_review` → `insert_case`
  - Return `AnalyzeResponse` including `disclaimer: "Research prototype — not for clinical use."`
  - Define Pydantic models: `FindingScore`, `SimilarCase`, `AnalyzeResponse`
  - _Requirements: 1.2, 2.1, 2.3, 2.4, 3.1, 3.2, 4.2, 4.3, 5.1, 5.2, 6.1, 6.2, 6.3, 7.1, 9.2_

  - [ ]* 9.1 Write property test for disclaimer in every response (P13)
    - **Property 13: Disclaimer is present in every analyze response**
    - Use `pytest-anyio` + `httpx.AsyncClient`; post fixture images via property test; assert `response.json()["disclaimer"]` is non-empty and contains `"not for clinical use"`
    - _Validates: Requirements 9.2_

  - [ ]* 9.2 Write unit tests for analyze route error cases
    - Test non-image file → HTTP 422
    - Test inference error → HTTP 500 with descriptive message
    - Test oversized file → HTTP 413
    - _Requirements: 1.3, 2.4_

- [x] 10. FastAPI queue routes
  - Create `app/routers/queue.py` with `GET /api/queue`, `GET /api/queue/{id}`, `PATCH /api/queue/{id}`
  - `GET /api/queue`: accept optional `status` query param; delegate to `get_queue`
  - `GET /api/queue/{id}`: delegate to `get_case`; return 404 if not found
  - `PATCH /api/queue/{id}`: accept `StatusUpdate` body (`{"status": "reviewed"}`); delegate to `update_case_status`; return 404 if not found
  - Define `CaseSummary`, `CaseDetail`, `StatusUpdate` Pydantic models
  - _Requirements: 7.2, 7.3, 7.4, 6.7_

  - [ ]* 10.1 Write unit tests for queue routes
    - Test `GET /api/queue?status=pending` returns only pending cases
    - Test `GET /api/queue/99999` returns HTTP 404
    - Test `PATCH /api/queue/{id}` transitions status and removes from pending view
    - Use in-memory SQLite seeded with fixture rows
    - _Requirements: 7.2, 7.3, 7.4, 6.7_

- [x] 11. Checkpoint — all backend routes pass tests
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. React app scaffold and global components
  - Scaffold Vite + React + React Router project in `src/`
  - Set up routes: `/` → `UploadView`, `/result/:id` → `ResultView`, `/queue` → `QueueView`
  - Create `Disclaimer` banner component (persistent on all views): "Research prototype — not for clinical use"
  - Add basic global CSS for layout and the disclaimer banner
  - _Requirements: 9.1, 9.3_

- [x] 13. UploadView
  - Create `src/UploadView.tsx`
  - File drag-and-drop + click-to-select (accept `.jpg,.jpeg,.png`)
  - Client-side MIME type validation; show inline error for non-image files, do not send request
  - Inline image preview via `URL.createObjectURL`
  - Loading spinner while `POST /api/analyze` is in-flight
  - On success navigate to `/result/:id`; on error show toast/inline error
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [ ]* 13.1 Write property test for invalid file type rejection (P2)
    - **Property 2: Invalid file type rejection**
    - Use `fast-check` to generate MIME type strings that are not `image/jpeg` or `image/png`; assert no fetch call is made and error message is displayed
    - _Validates: Requirements 1.3_

  - [ ]* 13.2 Write unit tests for UploadView
    - Valid image triggers `POST /api/analyze` (1.2)
    - Selecting a file sets preview src (1.1)
    - Loading indicator shown while request is in-flight (1.4)
    - _Requirements: 1.1, 1.2, 1.4_

- [x] 14. ResultView
  - Create `src/ResultView.tsx`
  - Fetch `GET /api/queue/:id` on mount; show "Case not found" error state on 404
  - Toggle button "Original" / "Heatmap" swaps `<img>` src
  - `BarChart` (Recharts) of all finding scores
  - Similar cases panel (list) with `uid`, `findings`, `impression` per case
  - Grounded explanation text block with label "AI-generated prototype output — not for clinical use"
  - "Mark Reviewed" button → `PATCH /api/queue/:id`; update local state on success
  - _Requirements: 3.3, 4.4, 5.3, 5.4, 6.6, 6.7, 9.3_

  - [ ]* 14.1 Write unit tests for ResultView
    - Heatmap toggle swaps image src (3.3)
    - Similar cases panel renders report text (4.4)
    - Explanation disclaimer label present (5.4)
    - "Case not found" shown on 404 (7.4)
    - _Requirements: 3.3, 4.4, 5.4, 7.4_

- [x] 15. QueueView
  - Create `src/QueueView.tsx`
  - Fetch `GET /api/queue` on mount (all statuses)
  - Two-lane layout: "Needs Review" lane (`status=needs_human_review`) and priority lane (remaining)
  - Case card: thumbnail, top finding, confidence badge, priority chip, timestamp
  - Client-side sort by priority or timestamp without page reload; implement `sortCases` helper
  - Click card → navigate to `/result/:id`
  - _Requirements: 6.4, 6.5, 6.6_

  - [ ]* 15.1 Write property test for client-side sort (P11)
    - **Property 11: Client-side sort produces a correctly ordered list**
    - Use `fast-check` to generate arrays of case objects; assert `High` before `Normal` for priority sort; assert ascending `created_at` for timestamp sort
    - Run 100 iterations
    - _Validates: Requirements 6.5_

  - [ ]* 15.2 Write unit tests for QueueView
    - `needs_human_review` cases appear in "Needs Review" lane (6.4)
    - Clicking a card navigates to ResultView (6.6)
    - _Requirements: 6.4, 6.6_

- [x] 16. Wire frontend to backend and handle edge states
  - Create `src/api.ts` with typed fetch helpers for all four endpoints
  - Add empty-state displays: no cases in queue, no similar cases found, explanation fallback text
  - Add error boundary / toast for unexpected API errors
  - Ensure `VITE_API_BASE_URL` or proxy config routes `/api` to the FastAPI server
  - _Requirements: 1.4, 2.4, 4.3, 5.2_

- [x] 17. Final checkpoint — all tests pass, README added
  - Add `README.md` with: project overview, setup steps (pip install, `build_index.py`, uvicorn, npm run dev), environment variables (`OPENAI_API_KEY`), disclaimer
  - Ensure all backend (`pytest --ignore=tests/slow`) and frontend (`vitest --run`) tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- The offline indexer (`scripts/build_index.py`) must be run once before first use
- Model-loading tests are marked `@pytest.mark.slow` and excluded from the default test run
- `OPENAI_API_KEY` is required for live explanations; the app degrades gracefully without it
- Property tests use `settings(max_examples=100)` (hypothesis) and `{ numRuns: 100 }` (fast-check)
