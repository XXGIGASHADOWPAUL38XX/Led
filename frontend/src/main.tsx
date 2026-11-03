import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@xyflow/react/dist/base.css";
import { BackendProvider } from "./api/backend-provider";
import { BackendStore } from "./api/store";
import App from "./app/app";
import "./styles/index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BackendProvider store={new BackendStore()}>
      <App />
    </BackendProvider>
  </StrictMode>,
);
