import Mustache from "mustache";
import { head, isEmpty, isNull, isUndefined } from "lodash";

export function buildAlertTemplateContext({
  alert,
  query,
  columnNames,
  resultValues,
  row = null,
  rowIndex = null,
  state = null,
}) {
  const host = typeof window !== "undefined" ? window.location.origin : "";
  const colName = alert.options?.column;
  const rows = resultValues || [];

  let resultValue = null;
  if (row && colName in row) {
    resultValue = row[colName];
  } else if (!isEmpty(rows) && colName in rows[0]) {
    resultValue = rows[0][colName];
  }

  const resultTable = rows.map(r => columnNames.map(name => r[name]));
  const byColumn = columnNames.reduce((acc, name) => {
    acc[name] = rows.reduce((colAcc, r, idx) => {
      colAcc[String(idx)] = r[name];
      return colAcc;
    }, {});
    return acc;
  }, {});

  const context = {
    ALERT_NAME: alert.name || "New Alert",
    ALERT_URL: alert.id ? `${host}/alerts/${alert.id}` : `${host}/alerts/new`,
    ALERT_STATUS: (state || alert.state || "TRIGGERED").toUpperCase(),
    ALERT_SELECTOR: alert.options?.selector || "first",
    ALERT_CONDITION: alert.options?.op || ">",
    ALERT_THRESHOLD: alert.options?.value ?? "",
    QUERY_NAME: query?.name || "",
    QUERY_URL: query?.id ? `${host}/queries/${query.id}` : "",
    QUERY_RESULT_VALUE: isNull(resultValue) || isUndefined(resultValue) ? "UNKNOWN" : resultValue,
    QUERY_RESULT_ROWS: rows,
    QUERY_RESULT_COLS: columnNames,
    QUERY_RESULT_TABLE: resultTable,
    QUERY_RESULT_ROW: row || (rows[0] || {}),
    QUERY_RESULT_ROW_INDEX: rowIndex ?? "",
    QUERY_RESULT_BY_COLUMN: byColumn,
  };

  columnNames.forEach(name => {
    if (row && name in row) {
      context[name] = row[name];
    } else {
      context[name] = byColumn[name] || {};
    }
  });

  return context;
}

export function renderAlertTemplate(template, context) {
  if (!template) {
    return "";
  }
  return Mustache.render(template, context);
}

export function looksLikeDiscordPayload(template) {
  if (!template) {
    return false;
  }
  const trimmed = template.trim();
  return trimmed.startsWith("{") && (trimmed.includes("embeds") || trimmed.includes("content"));
}
