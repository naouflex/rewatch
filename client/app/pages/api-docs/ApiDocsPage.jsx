import React from "react";
import routeWithUserSession from "@/components/ApplicationArea/routeWithUserSession";
import ScalarApiReference from "@/components/ApiDocs/ScalarApiReference";
import { clientConfig } from "@/services/auth";
import routes from "@/services/routes";

import "./ApiDocsPage.less";

function ApiDocsPage() {
  return (
    <div className="api-docs-page">
      <ScalarApiReference basePath={clientConfig.basePath} />
    </div>
  );
}

routes.register(
  "ApiDocs",
  routeWithUserSession({
    path: "/api-docs",
    title: "API",
    bodyClass: "fixed-layout",
    render: () => <ApiDocsPage />,
  })
);

export default ApiDocsPage;
