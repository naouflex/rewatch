import React, { useEffect, useState } from "react";

import ActivityBreakdown from "@/components/activity/ActivityBreakdown";
import ActivityHeatmap from "@/components/activity/ActivityHeatmap";
import ActivityWeekChart from "@/components/activity/ActivityWeekChart";
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
          <div className="home-activity__charts row">
            <div className="col-md-7">
              <div className="home-activity__panel">
                <h3 className="home-activity__panel-title">This week</h3>
                <ActivityWeekChart week={summary.week} />
              </div>
            </div>
            <div className="col-md-5">
              <div className="home-activity__panel home-activity__panel--breakdown">
                <h3 className="home-activity__panel-title">Breakdown</h3>
                <ActivityBreakdown
                  byAction={summary.by_action}
                  byObjectType={summary.by_object_type}
                />
              </div>
            </div>
          </div>
          <div className="home-activity__panel home-activity__panel--heatmap">
            <div className="home-activity__heatmap-header">
              <h3 className="home-activity__panel-title">Last 12 months</h3>
              <span className="home-activity__heatmap-meta">
                {summary.total} contribution{summary.total === 1 ? "" : "s"}
              </span>
            </div>
            <ActivityHeatmap daily={summary.daily} height={170} />
          </div>
        </div>
      )}
      {!loading && !summary && (
        <p className="home-activity__empty">Activity data is unavailable right now.</p>
      )}
    </HomeSection>
  );
}
