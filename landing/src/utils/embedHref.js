// Returns a react-router `to` value that preserves the current page's query
// string. This keeps embed mode (`?embed=1`) and parent-driven theme
// (`?theme=dark`) sticky as the user clicks around the help center.
export default function embedHref(path) {
  if (typeof window === "undefined") return path;
  const search = window.location.search || "";
  if (!search) return path;

  // path may already contain a hash (e.g. "/help/foo#section"); preserve it.
  const [pathname, hash = ""] = path.split("#");
  return {
    pathname,
    search,
    hash: hash ? `#${hash}` : "",
  };
}
