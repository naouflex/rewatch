import React from "react";
import PropTypes from "prop-types";

import { buildDiscordWebhookPayload } from "@/pages/alert/components/discordWebhookPreview";

import ConfigSection from "@/components/ConfigSection/ConfigSection";
import "@/components/ConfigSection/ConfigSection.less";

import "./DestinationTypePreview.less";

const TYPE_NOTES = {
  discord_webhook: {
    title: "Discord webhook",
    description:
      "By default, alerts send a status-colored embed with condition and links. Override with a custom Mustache JSON template on each alert's body field.",
  },
  webhook: {
    title: "Webhook",
    description:
      "POSTs JSON to your URL. Use alert custom_subject and custom_body (Mustache) for alert.title and alert.description in the payload.",
  },
  slack: {
    title: "Slack",
    description: "Uses alert custom_subject as attachment text and custom_body as a description field when triggered.",
  },
  email: {
    title: "Email",
    description: "Uses alert custom_subject and custom_body (Mustache, HTML allowed) when configured on the alert.",
  },
};

function DiscordDefaultPreview() {
  const sample = buildDiscordWebhookPayload({
    alert: {
      id: 1,
      name: "Example Alert",
      state: "triggered",
      options: { column: "value", op: ">", value: 100 },
    },
    query: { id: 1, name: "Example Query" },
    columnNames: ["value"],
    resultValues: [{ value: 142 }],
    customBody: null,
    state: "triggered",
  });

  return (
    <pre className="destination-type-preview__json">{JSON.stringify(sample.payload, null, 2)}</pre>
  );
}

export default function DestinationTypePreview({ type }) {
  if (!type) {
    return null;
  }

  const notes = TYPE_NOTES[type.type] || {
    title: type.name,
    description: "Configure this destination, then subscribe alerts or models to it.",
  };

  return (
    <ConfigSection title="How notifications look" className="destination-type-preview">
      <p className="destination-type-preview__description">{notes.description}</p>
      {type.type === "discord_webhook" && <DiscordDefaultPreview />}
      {type.type === "webhook" && (
        <pre className="destination-type-preview__json">
{`{
  "event": "triggered",
  "alert": {
    "name": "{{ALERT_NAME}}",
    "title": "<custom_subject>",
    "description": "<custom_body>"
  },
  "url_base": "https://..."
}`}
        </pre>
      )}
    </ConfigSection>
  );
}

DestinationTypePreview.propTypes = {
  type: PropTypes.object, // eslint-disable-line react/forbid-prop-types
};

DestinationTypePreview.defaultProps = {
  type: null,
};
