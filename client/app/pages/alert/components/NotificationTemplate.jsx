import React, { useState } from "react";
import PropTypes from "prop-types";

import HelpTrigger from "@/components/HelpTrigger";
import { Alert as AlertType, Query as QueryType } from "@/components/proptypes";

import Input from "antd/lib/input";
import Select from "antd/lib/select";
import { confirmDialog } from "@/components/ModalShell/confirmDialog";
import Switch from "antd/lib/switch";
import QuestionCircleOutlinedIcon from "@ant-design/icons/QuestionCircleOutlined";

import DiscordWebhookPreview from "./DiscordWebhookPreview";
import useDiscordDestination from "./useDiscordDestination";
import { looksLikeDiscordPayload, renderAlertTemplate, buildAlertTemplateContext } from "./alertTemplateUtils";

import "./NotificationTemplate.less";

function NotificationTemplate({
  alert,
  query,
  columnNames,
  resultValues,
  subject,
  setSubject,
  body,
  setBody,
  alertId,
  subscriptionsRefresh,
}) {
  const hasContent = !!(subject || body);
  const [enabled, setEnabled] = useState(hasContent ? 1 : 0);
  const [showEmailPreview, setShowEmailPreview] = useState(false);
  const { hasDiscordWebhook, destinationOptions } = useDiscordDestination(alertId, subscriptionsRefresh);

  const showDiscordPreview =
    !!enabled && (hasDiscordWebhook || looksLikeDiscordPayload(body) || !body);

  const templateContext = buildAlertTemplateContext({ alert, query, columnNames, resultValues });
  const render = tmpl => renderAlertTemplate(tmpl, templateContext);

  const onEnabledChange = value => {
    if (value || !hasContent) {
      setEnabled(value);
      setShowEmailPreview(false);
    } else {
      confirmDialog({
        title: "Are you sure?",
        description: "Switching to default template will discard your custom template.",
        onConfirm: () => {
          setSubject(null);
          setBody(null);
          setEnabled(value);
          setShowEmailPreview(false);
        },
      });
    }
  };

  return (
    <div className="alert-template">
      <Select
        value={enabled}
        onChange={onEnabledChange}
        optionLabelProp="label"
        popupMatchSelectWidth={false}
        style={{ width: "fit-content" }}>
        <Select.Option value={0} label="Use default template">
          Default template
        </Select.Option>
        <Select.Option value={1} label="Use custom template">
          Custom template
        </Select.Option>
      </Select>

      {!!enabled && (
        <div className="alert-custom-template" data-test="AlertCustomTemplate">
          {hasDiscordWebhook && (
            <p className="alert-template-hint">
              Discord webhook uses the <strong>body</strong> field as a Mustache template that renders to Discord JSON
              (<code>content</code>, <code>embeds</code>, …). Subject is used by email and other destinations only.
            </p>
          )}

          <label className="alert-template-field-label" htmlFor="custom-subject">
            Subject <span className="alert-template-field-label__optional">(email &amp; others)</span>
          </label>
          <Input
            id="custom-subject"
            value={showEmailPreview ? render(subject) : subject}
            aria-label="Subject"
            onChange={e => setSubject(e.target.value)}
            disabled={showEmailPreview}
            data-test="CustomSubject"
            placeholder="{{ALERT_NAME}} is {{ALERT_STATUS}}"
          />

          <label className="alert-template-field-label" htmlFor="custom-body">
            Body{" "}
            {hasDiscordWebhook && (
              <span className="alert-template-field-label__optional">(Discord webhook JSON template)</span>
            )}
          </label>
          <Input.TextArea
            id="custom-body"
            value={showEmailPreview ? render(body) : body}
            aria-label="Body"
            autoSize={{ minRows: 9 }}
            onChange={e => setBody(e.target.value)}
            disabled={showEmailPreview}
            data-test="CustomBody"
            placeholder={
              hasDiscordWebhook
                ? '{"content": "{{ALERT_NAME}} triggered", "embeds": [{"title": "Value: {{QUERY_RESULT_VALUE}}", "color": 15158332}]}'
                : "Notification body (Mustache)"
            }
          />

          {showDiscordPreview && (
            <DiscordWebhookPreview
              alert={alert}
              query={query}
              columnNames={columnNames}
              resultValues={resultValues}
              customBody={body}
              destinationOptions={destinationOptions}
              sendForEachRow={!!alert.options?.send_for_each_row}
            />
          )}

          <div className="alert-template-email-preview-toggle">
            Email / plain preview{" "}
            <Switch
              size="small"
              className="alert-template-preview"
              checked={showEmailPreview}
              onChange={setShowEmailPreview}
            />
          </div>

          <HelpTrigger type="ALERT_NOTIF_TEMPLATE_GUIDE" className="f-13">
            <QuestionCircleOutlinedIcon aria-hidden="true" /> Formatting guide
          </HelpTrigger>
        </div>
      )}

      {!!enabled && hasDiscordWebhook && !body && (
        <p className="alert-template-hint alert-template-hint--below">
          With an empty body, Discord receives the default status-colored embed (title, condition, links).
        </p>
      )}
    </div>
  );
}

NotificationTemplate.propTypes = {
  alert: AlertType.isRequired,
  query: QueryType.isRequired,
  columnNames: PropTypes.arrayOf(PropTypes.string).isRequired,
  resultValues: PropTypes.arrayOf(PropTypes.any).isRequired,
  subject: PropTypes.string,
  setSubject: PropTypes.func.isRequired,
  body: PropTypes.string,
  setBody: PropTypes.func.isRequired,
  alertId: PropTypes.any,
  subscriptionsRefresh: PropTypes.number,
};

NotificationTemplate.defaultProps = {
  subject: "",
  body: "",
  alertId: null,
  subscriptionsRefresh: 0,
};

export default NotificationTemplate;
