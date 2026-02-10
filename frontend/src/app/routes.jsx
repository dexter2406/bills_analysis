import { Navigate, Route, Routes } from "react-router-dom";
import { BillUploadPage } from "../features/upload/pages/BillUploadPage";
import { ManualReviewPage } from "../features/upload/pages/ManualReviewPage";
import { PlaceholderPage } from "./PlaceholderPage";

/**
 * Top-level route map for the frontend shell.
 */
export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<BillUploadPage />} />
      <Route path="/manual-review" element={<ManualReviewPage />} />
      <Route path="/archive" element={<PlaceholderPage title="Archive" description="Archive workspace will be implemented in next milestone." />} />
      <Route path="/settings" element={<PlaceholderPage title="Settings" description="Settings workspace will be implemented in next milestone." />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
