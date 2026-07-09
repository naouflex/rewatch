import React from "react";
import PropTypes from "prop-types";
import { get } from "lodash";

import Tag from "antd/lib/tag";

import ConfigSection from "@/components/ConfigSection/ConfigSection";
import "@/components/ConfigSection/ConfigSection.less";

import "./SnippetReadOnlyView.less";

export default function SnippetReadOnlyView({ querySnippet }) {
  return (
    <div className="snippet-readonly" data-test="SnippetReadOnlyView">
      <ConfigSection title="Details">
        <dl className="snippet-readonly__list">
          <div className="snippet-readonly__row">
            <dt>Trigger</dt>
            <dd>
              <code>{querySnippet.trigger}</code>
            </dd>
          </div>
          {querySnippet.description && (
            <div className="snippet-readonly__row">
              <dt>Description</dt>
              <dd>{querySnippet.description}</dd>
            </div>
          )}
          {get(querySnippet, "tags", []).length > 0 && (
            <div className="snippet-readonly__row">
              <dt>Tags</dt>
              <dd>
                {querySnippet.tags.map(tag => (
                  <Tag key={tag} color="blue">
                    {tag}
                  </Tag>
                ))}
              </dd>
            </div>
          )}
        </dl>
      </ConfigSection>

      <ConfigSection title="SQL template">
        <pre className="snippet-readonly__code">{querySnippet.snippet}</pre>
        <p className="snippet-readonly__hint">
          Type <code>:{querySnippet.trigger}</code> in the query editor to insert this SQL.
        </p>
      </ConfigSection>
    </div>
  );
}

SnippetReadOnlyView.propTypes = {
  querySnippet: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
};
