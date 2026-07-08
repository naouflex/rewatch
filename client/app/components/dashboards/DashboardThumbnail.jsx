import React, { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import classNames from "classnames";

import { getResolvedTheme, subscribeToTheme } from "@/services/theme";
import {
  blockieViewBox,
  buildDashboardBlockie,
  readBlockieThemeColors,
} from "./dashboardBlockie";

import "./DashboardThumbnail.less";

function ChartBlockieSvg({ dashboardId, size, colors, pattern }) {
  const { width, height } = blockieViewBox(size);
  const padding = 4;
  const chartLeft = padding + 1;
  const chartTop = padding + 6;
  const chartWidth = width - padding * 2 - 2;
  const chartHeight = height - padding - chartTop;
  const { variant, bars, linePoints, accent, secondary, showDots } = pattern;

  const barGap = 2;
  const barWidth = Math.max(2, (chartWidth - barGap * (bars.length + 1)) / bars.length);

  const lineCoords = linePoints.map((point, index) => {
    const x = chartLeft + point.x * chartWidth;
    const y = chartTop + chartHeight - point.y * chartHeight;
    return { x, y };
  });

  const linePath =
    lineCoords.length >= 2
      ? `M ${lineCoords.map(point => `${point.x.toFixed(1)} ${point.y.toFixed(1)}`).join(" L ")}`
      : null;

  return (
    <svg
      className="dashboard-thumbnail__svg"
      viewBox={`0 0 ${width} ${height}`}
      xmlns="http://www.w3.org/2000/svg"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
    >
      <rect x="0" y="0" width={width} height={height} fill={colors.bg} rx="4" />
      <rect
        x={chartLeft - 1}
        y={chartTop - 1}
        width={chartWidth + 2}
        height={chartHeight + 2}
        fill={colors.surface}
        stroke={colors.grid}
        rx="3"
      />

      {variant === 1 && linePath ? (
        <>
          <path
            d={`${linePath} L ${lineCoords[lineCoords.length - 1].x.toFixed(1)} ${(chartTop + chartHeight).toFixed(1)} L ${lineCoords[0].x.toFixed(1)} ${(chartTop + chartHeight).toFixed(1)} Z`}
            fill={`${accent}33`}
          />
          <path d={linePath} fill="none" stroke={accent} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          {showDots &&
            lineCoords.map((point, index) => (
              <circle key={index} cx={point.x} cy={point.y} r="1.4" fill={secondary} />
            ))}
        </>
      ) : (
        bars.map((value, index) => {
          const barHeight = value * (chartHeight - 4);
          const x = chartLeft + barGap + index * (barWidth + barGap);
          const y = chartTop + chartHeight - barHeight - 1;
          const fill = index % 3 === 0 ? accent : index % 3 === 1 ? secondary : colors.brand;
          return (
            <rect
              key={index}
              x={x}
              y={y}
              width={barWidth}
              height={barHeight}
              fill={fill}
              rx="1.2"
              opacity={variant === 2 && index % 2 === 1 ? 0.72 : 1}
            />
          );
        })
      )}

      <rect x={padding} y={padding} width={14} height={2.5} fill={colors.grid} rx="1" />
      <rect x={padding} y={padding + 4} width={9} height={2} fill={colors.grid} rx="1" opacity="0.7" />
    </svg>
  );
}

ChartBlockieSvg.propTypes = {
  dashboardId: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
  size: PropTypes.oneOf(["list", "home"]).isRequired,
  colors: PropTypes.shape({
    bg: PropTypes.string.isRequired,
    surface: PropTypes.string.isRequired,
    grid: PropTypes.string.isRequired,
    brand: PropTypes.string.isRequired,
    muted: PropTypes.string.isRequired,
  }).isRequired,
  pattern: PropTypes.shape({
    variant: PropTypes.number.isRequired,
    bars: PropTypes.arrayOf(PropTypes.number).isRequired,
    linePoints: PropTypes.arrayOf(
      PropTypes.shape({
        x: PropTypes.number.isRequired,
        y: PropTypes.number.isRequired,
      })
    ).isRequired,
    accent: PropTypes.string.isRequired,
    secondary: PropTypes.string.isRequired,
    showDots: PropTypes.bool.isRequired,
  }).isRequired,
};

export default function DashboardThumbnail({ dashboardId, alt, className, size }) {
  const [theme, setTheme] = useState(() => getResolvedTheme());

  useEffect(() => subscribeToTheme(({ resolved }) => setTheme(resolved)), []);

  const colors = useMemo(() => readBlockieThemeColors(), [theme]);
  const pattern = useMemo(() => buildDashboardBlockie(dashboardId), [dashboardId]);

  return (
    <span
      className={classNames("dashboard-thumbnail", `dashboard-thumbnail--${size}`, className)}
      title={alt || undefined}
      aria-label={alt || "Dashboard chart icon"}
      role="img"
    >
      <ChartBlockieSvg dashboardId={dashboardId} size={size} colors={colors} pattern={pattern} />
    </span>
  );
}

DashboardThumbnail.propTypes = {
  dashboardId: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
  alt: PropTypes.string,
  className: PropTypes.string,
  size: PropTypes.oneOf(["list", "home"]),
};

DashboardThumbnail.defaultProps = {
  alt: "",
  className: null,
  size: "list",
};
