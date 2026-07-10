# Requirements Document

## Introduction

A full-stack web prototype that allows a user to upload a chest X-ray image, runs it through a pretrained classification model to flag likely findings, overlays a Grad-CAM heatmap showing what the model focused on, and adds the result to a triage queue sortable by priority that can be marked as reviewed. No model training is performed — a pretrained off-the-shelf model is used exclusively. This system is a research/demo prototype and makes no clinical accuracy claims.

## Glossary

- **System**: The full-stack chest X-ray triage web application (React frontend + FastAPI backend).
- **Frontend**: The React single-page application served to the user's browser.
- **Backend**: The FastAPI Python server handling inference, persistence, and API requests.
- **Classifier**: The pretrained `torchxrayvision` DenseNet model (`densenet121-res224-all`) used for chest X-ray finding classification.
- **Grad-CAM_Generator**: The component that produces Grad-CAM saliency heatmaps using `pytorch-grad-cam` targeting the last convolutional block of the Classifier.
- **Queue**: The list of analyzed cases persisted in SQLite, each with a status of `pending` or `reviewed`.
- **Case**: A single analyzed X-ray record containing image metadata, finding scores, heatmap path, priority, and review status.
- **Priority**: A computed heuristic label (`High` or `Normal`) assigned to each Case. Labeled as a heuristic, not a clinical assessment.
- **UploadView**: The frontend component for selecting and submitting an X-ray image.
- **ResultView**: The frontend component displaying inference results, heatmap, and finding score chart for a single Case.
- **QueueView**: The frontend component displaying the full list of Cases in the Queue.
- **Indexer**: An offline script that runs all Frontal IU Chest X-ray images through the Classifier's feature layer and stores embedding vectors.
- **Retriever**: The component that performs cosine similarity search against indexed embeddings to find similar historical cases.
- **Explainer**: The component that constructs an LLM prompt using retrieved report text as context and returns a grounded explanation.

---

## Requirements

### Requirement 1: Image Upload

**User Story:** As a clinician or researcher, I want to upload a chest X-ray image from my device, so that I can submit it for automated analysis.

#### Acceptance Criteria

1. WHEN a user selects or drops a JPG or PNG file onto the UploadView, THE Frontend SHALL display an inline preview of the image before submission.
2. WHEN a user clicks "Analyze" with a valid image selected, THE Frontend SHALL send the image to the Backend via `POST /api/analyze`.
3. IF the selected file is not a JPG or PNG image, THEN THE Frontend SHALL display an inline error message and reject the upload without sending a request to the Backend.
4. WHILE the Backend is processing a submitted image, THE Frontend SHALL display a loading indicator to the user.

---

### Requirement 2: Inference

**User Story:** As a clinician or researcher, I want the system to classify findings in a submitted X-ray, so that I can see per-finding probability scores.

#### Acceptance Criteria

1. WHEN the Backend receives an image via `POST /api/analyze`, THE Classifier SHALL run inference and return per-finding probability scores for labels including at minimum: Pneumonia, Effusion, and No Finding.
2. WHEN the Classifier is loaded, THE Backend SHALL load the Classifier once at application startup and reuse it for all subsequent inference requests.
3. WHEN `POST /api/analyze` is called with a single image on CPU hardware, THE Backend SHALL return the complete response within 30 seconds.
4. IF the Backend encounters an error during inference, THEN THE Backend SHALL return an HTTP 500 response with a descriptive error message.

---

### Requirement 3: Explainability Overlay

**User Story:** As a clinician or researcher, I want to see a heatmap overlay showing which regions of the X-ray influenced the model's top finding, so that I can understand the model's focus.

#### Acceptance Criteria

1. WHEN inference completes for a submitted image, THE Grad-CAM_Generator SHALL generate a Grad-CAM heatmap for the highest-probability finding.
2. WHEN the Grad-CAM_Generator produces a heatmap, THE Backend SHALL overlay the heatmap on the original image and save the result as a static file accessible at a URL.
3. WHEN a Case is opened in the ResultView, THE Frontend SHALL display a toggle that switches between the original image and the heatmap overlay image.

---

### Requirement 4: Similar Case Retrieval

**User Story:** As a clinician or researcher, I want to see historically similar X-ray cases and their reports, so that I can put the model's findings in context.

#### Acceptance Criteria

1. THE Indexer SHALL process all Frontal-projection images from the IU Chest X-ray dataset, extract embedding vectors using the Classifier's feature layer, and persist those vectors alongside case metadata.
2. WHEN inference completes for a submitted image, THE Retriever SHALL compute cosine similarity between the query embedding and all indexed embeddings and return the top-5 most similar Cases.
3. WHEN the Retriever returns results, THE Backend SHALL include the retrieved cases' findings and impression text in the response payload.
4. WHEN a Case is opened in the ResultView, THE Frontend SHALL display a panel showing the top similar cases with their report text.

---

### Requirement 5: Grounded Explanation

**User Story:** As a clinician or researcher, I want a natural-language explanation grounded in retrieved report text, so that I can read a concise summary of the model's assessment in context.

#### Acceptance Criteria

1. WHEN the Retriever returns similar cases, THE Explainer SHALL construct a prompt using the retrieved report text as context and submit it to an LLM to generate a grounded explanation.
2. WHEN the Explainer returns a response, THE Backend SHALL include the explanation text in the `POST /api/analyze` response payload.
3. WHEN a Case is opened in the ResultView, THE Frontend SHALL display the grounded explanation text.
4. THE Frontend SHALL label the explanation as "AI-generated prototype output — not for clinical use" adjacent to the explanation text.

---

### Requirement 6: Triage Queue

**User Story:** As a clinician or researcher, I want a queue of all analyzed cases with priority indicators, so that I can triage cases efficiently.

#### Acceptance Criteria

1. WHEN inference completes for a submitted image, THE Backend SHALL add a Case to the Queue containing: thumbnail, top finding label, top finding confidence score, timestamp, priority, and status (`pending`).
2. THE Backend SHALL assign Priority `High` to a Case WHEN any finding probability score exceeds 0.7, and Priority `Normal` otherwise.
3. WHEN any finding score difference between the top-2 findings is less than or equal to 0.15, OR WHEN both top-2 finding scores are below 0.4, THE Backend SHALL set the Case status to `needs_human_review`.
4. THE QueueView SHALL display Cases in two lanes: a "Needs Review" lane for `needs_human_review` Cases and a priority-sorted lane for remaining Cases.
5. WHEN a user clicks sort controls in the QueueView, THE Frontend SHALL sort the Queue by the selected field (priority or timestamp) without reloading the page.
6. WHEN a user clicks a Case in the QueueView, THE Frontend SHALL navigate to the ResultView for that Case, displaying the full image, heatmap toggle, all finding scores, retrieved cases panel, and explanation.
7. WHEN a user clicks "Mark Reviewed" on a pending Case, THE Frontend SHALL send a `PATCH /api/queue/{id}` request and THE Backend SHALL update the Case status to `reviewed` and remove it from the pending Queue view.

---

### Requirement 7: Persistence

**User Story:** As a clinician or researcher, I want analyzed cases to survive a page refresh, so that I don't lose the triage queue between sessions.

#### Acceptance Criteria

1. THE Backend SHALL persist each Case to a SQLite database table `cases` with columns: `id`, `filename`, `top_finding`, `top_score`, `findings_json`, `heatmap_path`, `priority`, `status`, `created_at`.
2. WHEN `GET /api/queue` is called with a `status` query parameter, THE Backend SHALL return only Cases whose status matches the provided value, sorted by priority then `created_at`.
3. WHEN `GET /api/queue/{id}` is called, THE Backend SHALL return the full detail record for that Case.
4. IF a requested Case `id` does not exist, THEN THE Backend SHALL return an HTTP 404 response.

---

### Requirement 8: Dataset Integration

**User Story:** As a developer, I want the backend to load and join the IU Chest X-ray dataset, so that the Indexer and Retriever can reference real historical cases.

#### Acceptance Criteria

1. THE Indexer SHALL join `data/indiana_projections.csv` and `data/indiana_reports.csv` on the `uid` column and filter to rows where `projection` equals `"Frontal"`.
2. WHEN loading images from the dataset, THE Indexer SHALL open image files from `data/images/images_normalized/` using PIL regardless of file extension.
3. THE Indexer SHALL use the `findings` and `impression` fields from `indiana_reports.csv` as the report text associated with each indexed Case.

---

### Requirement 9: Prototype Labeling

**User Story:** As a developer, I want the application to clearly communicate its prototype status, so that no user mistakes it for a clinically validated tool.

#### Acceptance Criteria

1. THE Frontend SHALL display a persistent visible disclaimer on all views stating that the application is a research prototype and not for clinical use.
2. THE Backend SHALL include a `disclaimer` field in all `POST /api/analyze` responses with text stating the result is not for clinical use.
3. THE System SHALL not display any claims about clinical accuracy, sensitivity, specificity, or diagnostic equivalence anywhere in the UI or API responses.
