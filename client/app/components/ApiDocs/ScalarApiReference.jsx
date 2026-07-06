import React, { useEffect, useRef } from "react";
import PropTypes from "prop-types";
import { API_REFERENCE_SCALAR_CONFIG } from "@/config/brand";

function joinPath(basePath, segment) {
  const base = basePath || "/";
  return `${base.replace(/\/?$/, "/")}${segment.replace(/^\//, "")}`;
}

function mountScalar(host, { basePath, specUrl, bundleUrl }) {
  host.innerHTML = "";

  const configScript = document.createElement("script");
  configScript.id = "api-reference";
  configScript.type = "application/json";
  configScript.dataset.url = specUrl;
  configScript.dataset.configuration = JSON.stringify(API_REFERENCE_SCALAR_CONFIG);

  const bundleScript = document.createElement("script");
  bundleScript.src = bundleUrl;
  bundleScript.async = true;
  bundleScript.dataset.apiDocsBundle = "true";

  host.appendChild(configScript);
  host.appendChild(bundleScript);
}

function unmountScalar(host) {
  host.innerHTML = "";
  document.getElementById("api-reference")?.remove();
  document.querySelector('script[data-api-docs-bundle="true"]')?.remove();
  document.querySelector(".scalar-app")?.remove();
}

export default function ScalarApiReference({ basePath }) {
  const hostRef = useRef(null);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) {
      return undefined;
    }

    const specUrl = joinPath(basePath, "api/spec");
    const bundleUrl = joinPath(basePath, "api/docs/scalar.standalone.js");

    mountScalar(host, { basePath, specUrl, bundleUrl });

    return () => {
      unmountScalar(host);
    };
  }, [basePath]);

  return <div ref={hostRef} className="scalar-api-reference-host" />;
}

ScalarApiReference.propTypes = {
  basePath: PropTypes.string,
};

ScalarApiReference.defaultProps = {
  basePath: "/",
};
