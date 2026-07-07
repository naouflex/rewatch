import React, { useEffect, useState } from "react";
import Button from "antd/lib/button";

import Link from "@/components/Link";
import CreateDashboardDialog from "@/components/dashboards/CreateDashboardDialog";
import HelpTrigger from "@/components/HelpTrigger";
import { APPLICATION_TITLE } from "@/config/brand";
import { currentUser } from "@/services/auth";
import organizationStatus from "@/services/organizationStatus";
import UserActivity from "@/services/userActivity";

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

function formatActivityLine(summary) {
  if (!summary) {
    return null;
  }

  const parts = [];
  if (summary.week_total > 0) {
    parts.push(
      <>
        <strong>{summary.week_total}</strong> contribution{summary.week_total === 1 ? "" : "s"} this week
      </>
    );
  }
  if (summary.streak > 1) {
    parts.push(
      <>
        <strong>{summary.streak}</strong>-day streak
      </>
    );
  }

  if (!parts.length) {
    return "Your activity chart will fill in as you work with queries and dashboards.";
  }

  return parts.reduce((acc, part, index) => {
    if (index === 0) {
      return [part];
    }
    return [...acc, " · ", part];
  }, []);
}

export default function HomeHero() {
  const counters = organizationStatus.objectCounters || {};
  const statLine = formatStatLine(counters);
  const displayName = currentUser.name?.split(" ")[0] || "there";
  const [activitySummary, setActivitySummary] = useState(null);

  useEffect(() => {
    UserActivity.getSummary({ days: 365 })
      .then(setActivitySummary)
      .catch(() => setActivitySummary(null));
  }, []);

  const activityLine = formatActivityLine(activitySummary);
  const weekDelta = activitySummary?.week_change;

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
            {activityLine && (
              <p className="home-hero__activity">
                {activityLine}
                {typeof weekDelta === "number" && weekDelta !== 0 && (
                  <span
                    className={`home-hero__activity-delta ${
                      weekDelta > 0 ? "home-hero__activity-delta--up" : "home-hero__activity-delta--down"
                    }`}
                  >
                    {weekDelta > 0 ? `+${weekDelta}` : weekDelta} vs last week
                  </span>
                )}
              </p>
            )}
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
