import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { UploadView } from "./UploadView";
import { ResultView } from "./ResultView";
import { QueueView } from "./QueueView";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<UploadView />} />
        <Route path="/result/:id" element={<ResultView />} />
        <Route path="/queue" element={<QueueView />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
