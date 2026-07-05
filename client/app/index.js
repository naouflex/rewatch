import React from "react";
import { createRoot } from "react-dom/client";

// import "antd/dist/reset.css";


// Apply the saved theme as early as possible to avoid a flash of light theme
// when the user has chosen dark.
import "@/services/theme";

import "@/config";

import ApplicationArea from "@/components/ApplicationArea";
import offlineListener from "@/services/offline-listener";

const root = createRoot(document.getElementById("application-root"));
root.render(<ApplicationArea />);
offlineListener.init();
