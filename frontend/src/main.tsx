import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@xyflow/react/dist/base.css";
import { BackendProvider } from "./api/backend-provider";
import { backendUrl } from "./api/client";
import { BackendStore } from "./api/store";
import App from "./app/app";
import { TooltipProvider } from "./components/ui/tooltip";
import "./styles/index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={new QueryClient()}>
      <BackendProvider store={new BackendStore(backendUrl())}>
        <TooltipProvider>
          <App />
        </TooltipProvider>
      </BackendProvider>
    </QueryClientProvider>
  </StrictMode>,
);
