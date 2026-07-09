import React, { useMemo, useState } from "react";
import PropTypes from "prop-types";

import Segmented from "antd/lib/segmented";
import { Alert as AlertType, Query as QueryType } from "@/components/proptypes";

import { buildDiscordWebhookPayload, getEmbedAccentColor } from "./discordWebhookPreview";

import "./DiscordWebhookPreview.less";

function DiscordEmbed({ embed }) {
  if (!embed) {
    return null;
  }

  const accent = getEmbedAccentColor(embed);

  return (
    <div className="discord-preview__embed" style={{ borderLeftColor: accent }}>
      {embed.author?.name && (
        <div className="discord-preview__embed-author">
          {embed.author.icon_url && (
            <img src={embed.author.icon_url} alt="" className="discord-preview__embed-author-icon" />
          )}
          {embed.author.name}
        </div>
      )}
      {embed.title && <div className="discord-preview__embed-title">{embed.title}</div>}
      {embed.description && <div className="discord-preview__embed-description">{embed.description}</div>}
      {embed.fields?.length > 0 && (
        <div className="discord-preview__embed-fields">
          {embed.fields.map((field, index) => (
            <div
              key={index}
              className={`discord-preview__embed-field ${field.inline ? "discord-preview__embed-field--inline" : ""}`}>
              <div className="discord-preview__embed-field-name">{field.name}</div>
              <div className="discord-preview__embed-field-value">{field.value}</div>
            </div>
          ))}
        </div>
      )}
      {embed.footer?.text && <div className="discord-preview__embed-footer">{embed.footer.text}</div>}
    </div>
  );
}

DiscordEmbed.propTypes = {
  embed: PropTypes.object, // eslint-disable-line react/forbid-prop-types
};

DiscordEmbed.defaultProps = {
  embed: null,
};

function DiscordMessage({ payload }) {
  if (!payload) {
    return <div className="discord-preview__empty">No payload to preview.</div>;
  }

  return (
    <div className="discord-preview__message">
      {payload.username && <div className="discord-preview__username">{payload.username}</div>}
      {payload.content && <div className="discord-preview__content">{payload.content}</div>}
      {payload.embeds?.map((embed, index) => (
        <DiscordEmbed key={index} embed={embed} />
      ))}
    </div>
  );
}

DiscordMessage.propTypes = {
  payload: PropTypes.object, // eslint-disable-line react/forbid-prop-types
};

export default function DiscordWebhookPreview({
  alert,
  query,
  columnNames,
  resultValues,
  customBody,
  destinationOptions,
  sendForEachRow,
}) {
  const [previewMode, setPreviewMode] = useState("message");

  const previewRows = useMemo(() => {
    const rows = resultValues || [];
    if (sendForEachRow && rows.length > 1) {
      return rows.slice(0, 3).map((row, index) => ({ row, rowIndex: index }));
    }
    return [{ row: rows[0] || null, rowIndex: 0 }];
  }, [resultValues, sendForEachRow]);

  const previews = useMemo(
    () =>
      previewRows.map(({ row, rowIndex }) =>
        buildDiscordWebhookPayload({
          alert,
          query,
          columnNames,
          resultValues,
          customBody,
          state: alert.state || "triggered",
          row,
          rowIndex,
          destinationOptions,
        })
      ),
    [alert, query, columnNames, resultValues, customBody, destinationOptions, previewRows]
  );

  const primary = previews[0];

  return (
    <div className="discord-preview" data-test="DiscordWebhookPreview">
      <div className="discord-preview__toolbar">
        <span className="discord-preview__label">Discord webhook preview</span>
        <Segmented
          size="small"
          value={previewMode}
          onChange={setPreviewMode}
          options={[
            { label: "Message", value: "message" },
            { label: "JSON", value: "json" },
          ]}
        />
      </div>

      {primary.mode === "custom_content" && (
        <div className="discord-preview__note">
          Template did not render to valid JSON — Discord will receive this as plain <code>content</code>.
        </div>
      )}

      {previewMode === "message" ? (
        <div className="discord-preview__canvas">
          {previews.map((preview, index) => (
            <div key={index} className="discord-preview__item">
              {sendForEachRow && previews.length > 1 && (
                <div className="discord-preview__row-label">Row #{previewRows[index].rowIndex}</div>
              )}
              <DiscordMessage payload={preview.payload} />
            </div>
          ))}
        </div>
      ) : (
        <pre className="discord-preview__json">{JSON.stringify(primary.payload, null, 2)}</pre>
      )}
    </div>
  );
}

DiscordWebhookPreview.propTypes = {
  alert: AlertType.isRequired,
  query: QueryType.isRequired,
  columnNames: PropTypes.arrayOf(PropTypes.string).isRequired,
  resultValues: PropTypes.arrayOf(PropTypes.any).isRequired,
  customBody: PropTypes.string,
  destinationOptions: PropTypes.object,
  sendForEachRow: PropTypes.bool,
};

DiscordWebhookPreview.defaultProps = {
  customBody: null,
  destinationOptions: {},
  sendForEachRow: false,
};
