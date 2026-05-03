import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

// Returns true when the page is being rendered inside the host help drawer
// (an iframe) or when the URL has `?embed=1`. Components use this to drop
// chrome (navbar/footer/sidebar) so the drawer feels native — the drawer is
// only ~400px wide so we have to be deliberate about what we show.
export default function useEmbedMode() {
  const [embed, setEmbed] = useState(() => detectEmbed());
  const location = useLocation();

  useEffect(() => {
    setEmbed(detectEmbed());
  }, [location.pathname, location.search]);

  return embed;
}

function detectEmbed() {
  if (typeof window === "undefined") return false;
  const params = new URLSearchParams(window.location.search);
  if (params.get("embed") === "1") return true;
  try {
    return window.parent !== window;
  } catch {
    // Cross-origin parents may throw on access; treat that as embed.
    return true;
  }
}
