import React, { useEffect, useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import moment from "moment";
import Spin from "antd/lib/spin";
import * as echarts from "echarts/core";
import { BarChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

import AlertEvents from "@/services/alert-events";

import "./AlertHistoryChart.less";

echarts.use([BarChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer]);

const CHART_DAYS = 90;
const PAGE_SIZE = 250;
const MAX_PAGES = 4;

function readVar(name, fallback) {
  if (typeof document === "undefined") {
    return fallback;
  }
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

function shortDateLabel(value) {
  return moment(value).format("MMM D");
}

function bucketEventsByDay(events) {
  const buckets = new Map();

  events.forEach(event => {
    if (!event.created_at) {
      return;
    }
    const day = moment(event.created_at).format("YYYY-MM-DD");
    const bucket = buckets.get(day) || { date: day, ok: 0, error: 0, total: 0 };
    bucket.total += 1;
    if (event.status === "error") {
      bucket.error += 1;
    } else {
      bucket.ok += 1;
    }
    buckets.set(day, bucket);
  });

  const start = moment().subtract(CHART_DAYS - 1, "days").startOf("day");
  const series = [];

  for (let i = 0; i < CHART_DAYS; i += 1) {
    const date = start.clone().add(i, "days").format("YYYY-MM-DD");
    series.push(buckets.get(date) || { date, ok: 0, error: 0, total: 0 });
  }

  return series;
}

async function fetchChartEvents(alertId) {
  let page = 1;
  let all = [];
  let total = Infinity;

  while (page <= MAX_PAGES && all.length < total) {
    const response = await AlertEvents.forAlert({ alertId, page, pageSize: PAGE_SIZE });
    const results = response.results || [];
    total = response.count ?? results.length;
    all = all.concat(results);
    if (results.length < PAGE_SIZE) {
      break;
    }
    page += 1;
  }

  return all;
}

export default function AlertHistoryChart({ alertId, refreshToken }) {
  const containerRef = useRef(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const chartData = useMemo(() => bucketEventsByDay(events), [events]);
  const hasActivity = chartData.some(day => day.total > 0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchChartEvents(alertId)
      .then(results => {
        if (!cancelled) {
          setEvents(results);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setEvents([]);
          setError("Failed to load notification history for chart.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [alertId, refreshToken]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || loading || !hasActivity) {
      return undefined;
    }

    const text = readVar("--rd-color-text", "#1f1a16");
    const textMuted = readVar("--rd-color-text-muted", "#7a7068");
    const surface = readVar("--rd-color-surface", "#ffffff");
    const border = readVar("--rd-color-border", "#ece8e1");
    const divider = readVar("--rd-color-divider", "#f1eee8");
    const success = readVar("--rd-color-success", "#16a34a");
    const danger = readVar("--rd-color-danger", "#dc2626");
    const fontFamily = readVar(
      "--rd-font",
      '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
    );

    const chart = echarts.init(container);
    chart.setOption({
      backgroundColor: "transparent",
      grid: { left: 8, right: 8, top: 36, bottom: 24, containLabel: true },
      legend: {
        top: 0,
        right: 0,
        textStyle: { color: textMuted, fontFamily, fontSize: 11 },
        itemWidth: 10,
        itemHeight: 10,
      },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        backgroundColor: surface,
        borderColor: border,
        textStyle: { color: text, fontFamily },
        formatter(params) {
          const day = chartData[params[0]?.dataIndex];
          if (!day) {
            return "";
          }
          const lines = [`<strong>${moment(day.date).format("MMM D, YYYY")}</strong>`];
          params.forEach(item => {
            lines.push(`${item.marker} ${item.seriesName}: ${item.value}`);
          });
          lines.push(`Total: ${day.total}`);
          return lines.join("<br/>");
        },
      },
      xAxis: {
        type: "category",
        data: chartData.map(day => shortDateLabel(day.date)),
        axisLabel: {
          color: textMuted,
          fontFamily,
          fontSize: 11,
          interval: Math.max(0, Math.floor(chartData.length / 8) - 1),
        },
        axisLine: { lineStyle: { color: divider } },
        axisTick: { show: false },
      },
      yAxis: {
        type: "value",
        minInterval: 1,
        axisLabel: { color: textMuted, fontFamily, fontSize: 11 },
        splitLine: { lineStyle: { color: divider } },
      },
      series: [
        {
          name: "Delivered",
          type: "bar",
          stack: "notifications",
          data: chartData.map(day => day.ok),
          itemStyle: { color: success, borderRadius: [0, 0, 0, 0] },
          barMaxWidth: 18,
        },
        {
          name: "Failed",
          type: "bar",
          stack: "notifications",
          data: chartData.map(day => day.error),
          itemStyle: { color: danger, borderRadius: [4, 4, 0, 0] },
          barMaxWidth: 18,
        },
      ],
    });

    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(container);

    return () => {
      ro.disconnect();
      chart.dispose();
    };
  }, [chartData, hasActivity, loading]);

  return (
    <div className="alert-history-chart" data-test="AlertHistoryChart">
      <div className="alert-history-chart__header">
        <span className="alert-history-chart__title">Notifications (last {CHART_DAYS} days)</span>
      </div>
      {loading ? (
        <div className="alert-history-chart__placeholder">
          <Spin />
        </div>
      ) : error ? (
        <div className="alert-history-chart__placeholder alert-history-chart__placeholder--muted">{error}</div>
      ) : !hasActivity ? (
        <div className="alert-history-chart__placeholder alert-history-chart__placeholder--muted">
          No notifications recorded in the last {CHART_DAYS} days.
        </div>
      ) : (
        <div ref={containerRef} className="alert-history-chart__canvas" aria-label="Alert notification history chart" />
      )}
    </div>
  );
}

AlertHistoryChart.propTypes = {
  alertId: PropTypes.any.isRequired,
  refreshToken: PropTypes.number,
};

AlertHistoryChart.defaultProps = {
  refreshToken: 0,
};
