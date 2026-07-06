export const APPLICATION_TITLE = "Rewatch";

/** In-app route for the OpenAPI reference (Scalar), embedded in ApplicationLayout. */
export function getApiDocsUrl(basePath = "/") {
  return `${basePath}api-docs`;
}

/** Scalar UI options — keep in sync with ``rewatch/handlers/swagger.py`` if reused server-side. */
export function buildApiReferenceScalarConfig(resolvedTheme = "light") {
  const isDark = resolvedTheme === "dark";
  return {
    theme: "default",
    layout: "modern",
    darkMode: isDark,
    hideDarkModeToggle: true,
    defaultOpenAllTags: false,
    hideClientButton: false,
    hideDownloadButton: false,
    hideSearch: false,
    metaData: { title: "Rewatch API" },
  };
}

/** @deprecated Use buildApiReferenceScalarConfig(getResolvedTheme()) */
export const API_REFERENCE_SCALAR_CONFIG = buildApiReferenceScalarConfig("light");

export const BRAND_FONT_FAMILY = '"Inter", sans-serif';
