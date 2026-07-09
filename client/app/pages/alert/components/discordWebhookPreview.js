import { renderAlertTemplate, buildAlertTemplateContext } from "./alertTemplateUtils";

const DISCORD_COLOR = {
  ok: 0x2ecc71,
  triggered: 0xe74c3c,
  unknown: 0xf1c40f,
};

const DEFAULT_EMBED_TITLE = "Alert: {{ALERT_NAME}} is {{ALERT_STATUS}}";

function intToHexColor(color) {
  if (typeof color !== "number") {
    return null;
  }
  return `#${color.toString(16).padStart(6, "0").slice(-6)}`;
}

function buildDefaultEmbedPayload({ alert, query, columnNames, resultValues, state, row, rowIndex }) {
  const context = buildAlertTemplateContext({
    alert,
    query,
    columnNames,
    resultValues,
    row,
    rowIndex,
    state,
  });
  const host = typeof window !== "undefined" ? window.location.origin : "";
  const title = renderAlertTemplate(DEFAULT_EMBED_TITLE, context);

  const fields = [
    { name: "Query", value: `${host}/queries/${query?.id}`, inline: true },
    { name: "Alert", value: `${host}/alerts/${alert?.id}`, inline: true },
  ];

  if (alert.options?.column && alert.options?.op) {
    fields.push({
      name: "Condition",
      value: `\`${alert.options.column} ${alert.options.op} ${alert.options.value}\``,
      inline: false,
    });
  }

  if (row) {
    const preview = Object.entries(row)
      .slice(0, 10)
      .map(([k, v]) => `${k}=${v}`)
      .join(", ");
    fields.push({
      name: `Row #${rowIndex}`,
      value: preview || "(empty)",
      inline: false,
    });
  }

  const embed = {
    title,
    color: DISCORD_COLOR[state] || DISCORD_COLOR.unknown,
    fields,
  };

  return { embeds: [embed] };
}

export function buildDiscordWebhookPayload({
  alert,
  query,
  columnNames,
  resultValues,
  customBody,
  state = "triggered",
  row = null,
  rowIndex = null,
  destinationOptions = {},
}) {
  const context = buildAlertTemplateContext({
    alert,
    query,
    columnNames,
    resultValues,
    row,
    rowIndex,
    state,
  });

  let payload;
  let mode;
  let rendered = "";

  if (customBody) {
    rendered = renderAlertTemplate(customBody, context);
    try {
      payload = JSON.parse(rendered);
      mode = "custom_json";
    } catch {
      payload = { content: rendered };
      mode = "custom_content";
    }
  } else {
    payload = buildDefaultEmbedPayload({
      alert,
      query,
      columnNames,
      resultValues,
      state,
      row,
      rowIndex,
    });
    mode = "default_embed";
    rendered = JSON.stringify(payload, null, 2);
  }

  if (destinationOptions.username) {
    payload = { ...payload, username: destinationOptions.username };
  }
  if (destinationOptions.avatar_url) {
    payload = { ...payload, avatar_url: destinationOptions.avatar_url };
  }

  return { payload, mode, rendered, context };
}

export function getEmbedAccentColor(embed) {
  return intToHexColor(embed?.color) || "#f1c40f";
}

export { intToHexColor };
