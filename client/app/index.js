import React from "react";
import ReactDOM from "react-dom";

// Apply the saved theme as early as possible to avoid a flash of light theme
// when the user has chosen dark.
import "@/services/theme";

import "@/config";

import ApplicationArea from "@/components/ApplicationArea";
import offlineListener from "@/services/offline-listener";

ReactDOM.render(<ApplicationArea />, document.getElementById("application-root"), () => {
  offlineListener.init();
});
