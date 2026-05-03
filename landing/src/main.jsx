import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

// Apply the resolved theme (URL > postMessage > localStorage > system) to
// <html data-theme=…> synchronously, before React mounts, so we never flash
// the wrong palette.
import "./services/theme.js";
import App from "./App.jsx";
import "./styles/globals.css";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
