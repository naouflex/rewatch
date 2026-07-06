export const APPLICATION_TITLE = "Rewatch";

/** In-app route for the OpenAPI reference (Scalar), embedded in ApplicationLayout. */
export function getApiDocsUrl(basePath = "/") {
  return `${basePath}api-docs`;
}

/** Scalar UI options — keep in sync with ``rewatch/handlers/swagger.py`` template. */
export const API_REFERENCE_SCALAR_CONFIG = {
  theme: "default",
  layout: "modern",
  defaultOpenAllTags: false,
  hideClientButton: false,
  hideDownloadButton: false,
  hideSearch: false,
  metaData: { title: "Rewatch API" },
};

export const BRAND_FONT_FAMILY = '"Inter", sans-serif';
