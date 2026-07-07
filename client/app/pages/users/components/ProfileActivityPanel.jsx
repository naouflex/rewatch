import React, { useEffect, useState } from "react";

import ActivityBreakdown from "@/components/activity/ActivityBreakdown";
import ActivityHeatmap from "@/components/activity/ActivityHeatmap";
import ActivityWeekChart from "@/components/activity/ActivityWeekChart";
import UserActivity from "@/services/userActivity";

import "@/pages/home/components/HomeActivity.less";

function formatDelta(change) {
  if (change > 0) {
    return `+${change} vs last week`;
  }
  if (change < 0) {
    return `${change} vs last week`;
  }
  return "same as last week";
}

export default function ProfileActivityPanel() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    UserActivity.getSummary({ days: 365 })
      .then(setSummary)
      .catch(() => setSummary(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <p>Loading activity...</p>;
  }

  if (!summary) {
    return null;
  }

  return (
    <div className="profile-activity">
      <h3 className="profile-activity__title">Activity</h3>
      <div className="profile-activity__stats">
        <div className="profile-activity__stat">
          <span className="profile-activity__stat-value">{summary.week_total}</span>
          <span className="profile-activity__stat-label">This week</span>
        </div>
        <div className="profile-activity__stat">
          <span className="profile-activity__stat-value">{summary.streak}</span>
          <span className="profile-activity__stat-label">Day streak</span>
        </div>
        <div className="profile-activity__stat">
          <span className="profile-activity__stat-value">{summary.total}</span>
          <span className="profile-activity__stat-label">Last 12 months</span>
        </div>
      </div>
      <div className="home-activity">
        <div className="home-activity__panel">
          <h4 className="home-activity__panel-title">This week ({formatDelta(summary.week_change)})</h4>
          <ActivityWeekChart week={summary.week} height={150} />
        </div>
        <div className="home-activity__panel home-activity__panel--breakdown m-t-15">
          <h4 className="home-activity__panel-title">Breakdown</h4>
          <ActivityBreakdown byAction={summary.by_action} byObjectType={summary.by_object_type} />
        </div>
        <div className="home-activity__panel home-activity__panel--heatmap m-t-15">
          <ActivityHeatmap daily={summary.daily} height={170} />
        </div>
      </div>
    </div>
  );
}
