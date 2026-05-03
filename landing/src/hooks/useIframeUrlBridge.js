import { useEffect } from "react";
import { useLocation } from "react-router-dom";

// Every time the URL changes inside this site, post a message to the
// parent window so the in-app help drawer can show "open in new window"
// pointing at the page the user is actually looking at.
//
// The host side listens for `{ type: "iframe_url", message: "<url>" }`
// (see client/app/components/HelpTrigger.jsx -> onPostMessageReceived).
const IFRAME_URL_UPDATE_MESSAGE = "iframe_url";

export default function useIframeUrlBridge() {
  const location = useLocation();

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.parent === window) return; // not in an iframe

    try {
      // Send the parent the *clean* URL — without internal embed plumbing
      // (`?embed=1`, `?theme=…`, `?dark=…`) — so the drawer's
      // "open in new tab" button gives the standalone view.
      const url = new URL(window.location.href);
      ["embed", "theme", "dark"].forEach((p) => url.searchParams.delete(p));
      const cleanHref =
        url.origin +
        url.pathname +
        (url.search ? url.search : "") +
        (url.hash || "");

      window.parent.postMessage(
        {
          type: IFRAME_URL_UPDATE_MESSAGE,
          message: cleanHref,
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
