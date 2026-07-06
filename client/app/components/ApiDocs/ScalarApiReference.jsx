import React, { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import { buildApiReferenceScalarConfig } from "@/config/brand";
import { getResolvedTheme, subscribeToTheme } from "@/services/theme";

function joinPath(basePath, segment) {
  const base = basePath || "/";
  return `${base.replace(/\/?$/, "/")}${segment.replace(/^\//, "")}`;
}

function cleanupScalarMount(host) {
  if (host) {
    host.innerHTML = "";
  }
  document.getElementById("api-reference")?.remove();
  document.querySelectorAll('script[data-api-docs-bundle="true"]').forEach(el => el.remove());
  document.querySelector(".scalar-app")?.remove();
}

function mountScalar(host, { specUrl, bundleUrl, resolvedTheme }) {
  cleanupScalarMount(host);

  const configScript = document.createElement("script");
  configScript.id = "api-reference";
  configScript.type = "application/json";
  configScript.dataset.url = specUrl;
  configScript.dataset.configuration = JSON.stringify(buildApiReferenceScalarConfig(resolvedTheme));

  const bundleScript = document.createElement("script");
  // Cache-bust so Scalar re-initializes when the app theme changes.
  bundleScript.src = `${bundleUrl}?theme=${encodeURIComponent(resolvedTheme)}`;
  bundleScript.async = true;
  bundleScript.dataset.apiDocsBundle = "true";

  host.appendChild(configScript);
  host.appendChild(bundleScript);
}

export default function ScalarApiReference({ basePath }) {
  const hostRef = useRef(null);
  const [resolvedTheme, setResolvedTheme] = useState(() => getResolvedTheme());

  useEffect(() => subscribeToTheme(({ resolved }) => setResolvedTheme(resolved)), []);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) {
      return undefined;
    }

    const specUrl = joinPath(basePath, "api/spec");
    const bundleUrl = joinPath(basePath, "api/docs/scalar.standalone.js");

    mountScalar(host, { specUrl, bundleUrl, resolvedTheme });

    return () => {
      cleanupScalarMount(host);
    };
  }, [basePath, resolvedTheme]);

  return <div ref={hostRef} className="scalar-api-reference-host" data-theme={resolvedTheme} />;
}

ScalarApiReference.propTypes = {
  basePath: PropTypes.string,
};

ScalarApiReference.defaultProps = {
  basePath: "/",
};
