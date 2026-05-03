import React, { useEffect, useState } from "react";
import {
  getResolvedTheme,
  getThemePreference,
  setThemePreference,
  subscribeToTheme,
  toggleTheme,
} from "@/services/theme";

// `useTheme` was a custom hook in inverse-watch's ThemeProvider. Redash exposes
// the same primitives through the imperative `services/theme` module instead.
// To minimise diffs in the ported MLModel components, we re-expose the same
// hook here on top of redash's existing service.
//
// Returns:
//   - `isDarkMode`: boolean, true when the resolved theme is "dark"
//   - `theme`: the resolved theme name ("light" | "dark")
//   - `preference`: the user's stored preference ("light" | "dark" | "system")
//   - `setTheme`: setter for the preference
//   - `toggle`: cycle between light <-> dark
export function useTheme() {
  const [resolved, setResolved] = useState(() => getResolvedTheme());
  const [preference, setPreference] = useState(() => getThemePreference());

  useEffect(() => {
    const unsubscribe = subscribeToTheme(({ preference: pref, resolved: res }) => {
      setPreference(pref);
      setResolved(res);
    });
    return unsubscribe;
  }, []);

  return {
    isDarkMode: resolved === "dark",
    theme: resolved,
    preference,
    setTheme: setThemePreference,
    toggle: toggleTheme,
  };
}

// Some ported components also import a default `ThemeProvider` wrapper. Redash
// applies the theme imperatively (see `services/theme`), so the provider here
// is a no-op pass-through that just renders its children.
export default function ThemeProvider({ children }) {
  return <React.Fragment>{children}</React.Fragment>;
}
