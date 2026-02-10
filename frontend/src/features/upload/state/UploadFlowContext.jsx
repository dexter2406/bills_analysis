import { createContext, useContext, useMemo } from "react";
import { createUploadClient } from "../api/uploadClient";
import { useUploadFlow } from "./useUploadFlow";

const UploadFlowContext = createContext(null);

/**
 * Provide one shared upload-flow store for all upload/review routes.
 * @param {{ children: import("react").ReactNode }} props
 */
export function UploadFlowProvider({ children }) {
  const client = useMemo(() => createUploadClient(), []);
  const flow = useUploadFlow({ client });
  const value = useMemo(() => ({ client, ...flow }), [client, flow]);

  return <UploadFlowContext.Provider value={value}>{children}</UploadFlowContext.Provider>;
}

/**
 * Access shared upload-flow context.
 */
export function useUploadFlowContext() {
  const context = useContext(UploadFlowContext);
  if (!context) {
    throw new Error("useUploadFlowContext must be used within UploadFlowProvider.");
  }
  return context;
}

