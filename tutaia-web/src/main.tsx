import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ClerkProvider } from "@clerk/clerk-react";
import App from "./App";
import "./index.css";

const clerkKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

if (!clerkKey) {
  throw new Error("VITE_CLERK_PUBLISHABLE_KEY is required");
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ClerkProvider
      publishableKey={clerkKey}
      appearance={{
        variables: {
          colorPrimary: "#a78bfa",
          colorBackground: "#1a1a2e",
          colorInputBackground: "#2a2a40",
          colorInputText: "#ffffff",
          colorText: "#ffffff",
          colorTextSecondary: "#c4c4d4",
          colorDanger: "#f87171",
          borderRadius: "8px",
        },
      }}
    >
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ClerkProvider>
  </React.StrictMode>
);
