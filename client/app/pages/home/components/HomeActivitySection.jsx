import React, { useEffect, useState } from "react";

import ActivityHeatmap from "@/components/activity/ActivityHeatmap";
import UserActivity from "@/services/userActivity";

import HomeSection from "./HomeSection";

import "./HomeActivity.less";

export default function HomeActivitySection() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    UserActivity.getSummary({ days: 365 })
      .then(setSummary)
      .catch(() => setSummary(null))
      .finally(() => setLoading(false));
  }, []);

  return (
    <HomeSection title="Your activity" loading={loading}>
      {summary && (
        <div className="home-activity">
          <div className="home-activity__panel home-activity__panel--heatmap">
            <div className="home-activity__heatmap-header">
              <h3 className="home-activity__panel-title">Last 12 months</h3>
              <span className="home-activity__heatmap-meta">
                {summary.total} contribution{summary.total === 1 ? "" : "s"}
              </span>
            </div>
            {summary.total > 0 ? (
              <ActivityHeatmap daily={summary.daily} />
            ) : (
              <p className="home-activity__empty">
                Run queries, edit dashboards, or create content to start building your activity history.
              </p>
            )}
          </div>
        </div>
      )}
      {!loading && !summary && (
        <p className="home-activity__empty">Activity data is unavailable right now.</p>
      )}
    </HomeSection>
  );
}
