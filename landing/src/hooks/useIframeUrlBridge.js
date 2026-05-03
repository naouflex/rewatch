import { useEffect } from "react";
import { useLocation } from "react-router-dom";

// Mirrors the behavior the redash.io help site has: every time the URL
// changes, post a message to the parent window so the in-app help drawer
// can show "open in new window" pointing at the page the user is actually
// looking at.
//
// The Redash side listens for `{ type: "iframe_url", message: "<url>" }`
// (see client/app/components/HelpTrigger.jsx -> onPostMessageReceived).
const IFRAME_URL_UPDATE_MESSAGE = "iframe_url";

export default function useIframeUrlBridge() {
  const location = useLocation();

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.parent === window) return; // not in an iframe

    try {
      window.parent.postMessage(
        {
          type: IFRAME_URL_UPDATE_MESSAGE,
          message: window.location.href,
        },
        "*"
      );
    } catch (err) {
      // Cross-origin parents may reject postMessage in some browsers; the
      // drawer simply falls back to the initial URL in that case.
      // eslint-disable-next-line no-console
      console.debug("iframe_url postMessage failed:", err);
    }
  }, [location]);
}
