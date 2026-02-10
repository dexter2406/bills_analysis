import { BrowserRouter } from "react-router-dom";
import { AppRoutes } from "./routes";
import { UploadFlowProvider } from "../features/upload/state/UploadFlowContext";

/**
 * Root application component that provides routing context.
 */
export function App() {
  return (
    <BrowserRouter>
      <UploadFlowProvider>
        <AppRoutes />
      </UploadFlowProvider>
    </BrowserRouter>
  );
}
