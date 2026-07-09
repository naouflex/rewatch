import React from "react";
import PropTypes from "prop-types";

import PlainButton from "@/components/PlainButton";
import { Alert as AlertType, Query as QueryType } from "@/components/proptypes";

import DiscordWebhookPreview from "./DiscordWebhookPreview";
import useDiscordDestination from "./useDiscordDestination";
import { looksLikeDiscordPayload, renderAlertTemplate, buildAlertTemplateContext } from "./alertTemplateUtils";

import "./NotificationTemplateView.less";

const DEFAULT_SUBJECT = "Alert: {{ALERT_NAME}} changed status to {{ALERT_STATUS}}";
const DEFAULT_BODY = "Alert {{ALERT_NAME}} is {{ALERT_STATUS}}.\nValue: {{QUERY_RESULT_VALUE}}";

function previewLines(text, maxLines = 2) {
  if (!text) {
    return [];
  }
  return text.split("\n").slice(0, maxLines);
}

export default function NotificationTemplateView({
  alert,
  query,
  columnNames,
  resultValues,
  subject,
  body,
  onEdit,
  canEdit,
  subscriptionsRefresh,
}) {
  const { hasDiscordWebhook, destinationOptions } = useDiscordDestination(alert.id, subscriptionsRefresh);
  const hasCustom = !!(subject || body);
  const context = buildAlertTemplateContext({ alert, query, columnNames, resultValues });
  const displaySubject = renderAlertTemplate(hasCustom ? subject || "" : DEFAULT_SUBJECT, context);
  const displayBody = renderAlertTemplate(hasCustom ? body || "" : DEFAULT_BODY, context);
  const bodyLines = previewLines(displayBody);
  const showDiscordPreview = hasDiscordWebhook || looksLikeDiscordPayload(body);

  return (
    <div className="alert-template-view" data-test="NotificationTemplateView">
      <div className="alert-template-view__type">
        {hasCustom ? "Custom template" : "Default template"}
        {canEdit && onEdit && (
          <>
            {" · "}
            <PlainButton className="alert-template-view__edit-link" onClick={onEdit}>
              Edit template
            </PlainButton>
          </>
        )}
      </div>

      {showDiscordPreview ? (
        <DiscordWebhookPreview
          alert={alert}
          query={query}
          columnNames={columnNames}
          resultValues={resultValues}
          customBody={hasCustom ? body : null}
          destinationOptions={destinationOptions}
          sendForEachRow={!!alert.options?.send_for_each_row}
        />
      ) : (
        <div className="alert-template-view__preview">
          <div className="alert-template-view__subject">{displaySubject || "(no subject)"}</div>
          {bodyLines.map((line, index) => (
            <div key={index} className="alert-template-view__body-line">
              {line || "\u00a0"}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

NotificationTemplateView.propTypes = {
  alert: AlertType.isRequired,
  query: QueryType.isRequired,
  columnNames: PropTypes.arrayOf(PropTypes.string).isRequired,
  resultValues: PropTypes.arrayOf(PropTypes.any).isRequired,
  subject: PropTypes.string,
  body: PropTypes.string,
  onEdit: PropTypes.func,
  canEdit: PropTypes.bool,
  subscriptionsRefresh: PropTypes.number,
};

NotificationTemplateView.defaultProps = {
  subject: null,
  body: null,
  onEdit: null,
  canEdit: false,
  subscriptionsRefresh: 0,
};
