import React from "react";
import Button from "antd/lib/button";

import Link from "@/components/Link";
import CreateDashboardDialog from "@/components/dashboards/CreateDashboardDialog";
import HelpTrigger from "@/components/HelpTrigger";
import { APPLICATION_TITLE } from "@/config/brand";
import { currentUser } from "@/services/auth";
import organizationStatus from "@/services/organizationStatus";

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) {
    return "Good morning";
  }
  if (hour < 18) {
    return "Good afternoon";
  }
  return "Good evening";
}

function formatStatLine(counters) {
  const parts = [];
  if (counters.dashboards > 0) {
    parts.push(`${counters.dashboards} dashboard${counters.dashboards === 1 ? "" : "s"}`);
  }
  if (counters.queries > 0) {
    parts.push(`${counters.queries} quer${counters.queries === 1 ? "y" : "ies"}`);
  }
  if (counters.alerts > 0) {
    parts.push(`${counters.alerts} alert${counters.alerts === 1 ? "" : "s"}`);
  }
  if (counters.data_sources > 0) {
    parts.push(`${counters.data_sources} data source${counters.data_sources === 1 ? "" : "s"}`);
  }
  return parts.join(" · ");
}

export default function HomeHero() {
  const counters = organizationStatus.objectCounters || {};
  const statLine = formatStatLine(counters);
  const displayName = currentUser.name?.split(" ")[0] || "there";

  return (
    <div className="tile home-hero m-b-15">
      <div className="t-body tb-padding">
        <div className="home-hero__content">
          <div className="home-hero__text">
            <h2 className="home-hero__title">
              {getGreeting()}, {displayName}
            </h2>
            <p className="home-hero__subtitle">
              {statLine ? (
                <>
                  Your {APPLICATION_TITLE} workspace has {statLine}.
                </>
              ) : (
                <>Welcome back to {APPLICATION_TITLE}.</>
              )}
            </p>
          </div>
          <div className="home-hero__actions">
            {currentUser.hasPermission("create_query") && (
              <Link.Button href="queries/new" type="primary">
                New query
              </Link.Button>
            )}
            {currentUser.hasPermission("create_dashboard") && (
              <Button onClick={() => CreateDashboardDialog.showModal()}>New dashboard</Button>
            )}
            {currentUser.isAdmin && <Link.Button href="data_sources">Data sources</Link.Button>}
            <HelpTrigger className="home-hero__help" type="GETTING_STARTED" showTooltip={false}>
              Help
            </HelpTrigger>
          </div>
        </div>
      </div>
    </div>
  );
}
