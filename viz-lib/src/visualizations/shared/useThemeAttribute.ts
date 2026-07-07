import { useEffect, useState } from "react";

export default function useThemeAttribute() {
  const [theme, setTheme] = useState(() =>
    typeof document !== "undefined" ? document.documentElement.getAttribute("data-theme") : null
  );

  useEffect(() => {
    const observer = new MutationObserver(() => {
      setTheme(document.documentElement.getAttribute("data-theme"));
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, []);

  return theme;
}
