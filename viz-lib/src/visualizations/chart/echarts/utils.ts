import { isUndefined } from "lodash";
import moment from "moment";

export function cleanNumber(value: any) {
  if (isUndefined(value)) {
    return value;
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (trimmed === "") {
      return undefined;
    }
    const num = Number(trimmed);
    return Number.isFinite(num) ? num : value;
  }
  if (typeof value === "number" && !Number.isFinite(value)) {
    return undefined;
  }
  return value;
}

export function getSeriesAxis(series: any, options: any) {
  const seriesOptions = options.seriesOptions[series.name] || { type: options.globalSeriesType };
  if (seriesOptions.yAxis === 1 && (!options.series.stacking || seriesOptions.type === "line")) {
    return "y2";
  }
  return "y";
}

export function normalizeValue(value: any, axisType: any, dateTimeFormat = "YYYY-MM-DD HH:mm:ss") {
  if (axisType === "datetime" && moment.utc(value).isValid()) {
    value = moment.utc(value);
  }
  if (moment.isMoment(value)) {
    return value.format(dateTimeFormat);
  }
  return value;
}

/** Resolve "Auto Detect" (-) axis scale from sample x values. */
export function resolveAxisType(type: string, sampleValues: any[]): string {
  if (type && type !== "-") {
    return type;
  }

  const samples = sampleValues.filter(v => v != null && v !== "");
  if (samples.length === 0) {
    return "category";
  }

  const isDate = (v: any) => moment.utc(v).isValid() && /^\d{4}-\d{2}-\d{2}/.test(String(v));
  if (samples.every(isDate)) {
    return "datetime";
  }

  const isNumeric = (v: any) =>
    typeof v === "number" || (typeof v === "string" && v.trim() !== "" && Number.isFinite(Number(v)));
  if (samples.every(isNumeric)) {
    return "linear";
  }

  return "category";
}

export function computeBoxplotStats(values: number[]): number[] {
  if (values.length === 0) {
    return [0, 0, 0, 0, 0];
  }
  const sorted = [...values].sort((a, b) => a - b);
  const q = (p: number) => {
    const pos = (sorted.length - 1) * p;
    const base = Math.floor(pos);
    const rest = pos - base;
    if (sorted[base + 1] !== undefined) {
      return sorted[base] + rest * (sorted[base + 1] - sorted[base]);
    }
    return sorted[base];
  };
  return [sorted[0], q(0.25), q(0.5), q(0.75), sorted[sorted.length - 1]];
}
