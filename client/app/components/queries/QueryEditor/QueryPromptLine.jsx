import React, { useCallback, useState } from "react";
import PropTypes from "prop-types";
import cx from "classnames";
import { get } from "lodash";
import LoadingOutlined from "@ant-design/icons/LoadingOutlined";
import ThunderboltOutlined from "@ant-design/icons/ThunderboltOutlined";
import Tooltip from "@/components/Tooltip";
import notification from "@/services/notification";
import Assistant from "@/services/assistant";

import "./QueryPromptLine.less";

const PROMPT_PLACEHOLDERS = {
  yaml: "Describe the API data you want (e.g. Ethereum price history for 30 days)",
  json: "Describe the query in plain language (JSON query structure will be generated)",
  graphql: "Describe the GraphQL data you need (e.g. list users with id and name)",
  python: "Describe what the Python script should fetch or compute",
  sql: "Describe what you want in plain language, then press Enter",
};

function promptPlaceholder(syntax, dataSourceType) {
  if (dataSourceType === "coingecko") {
    return "e.g. Bitcoin price chart for the last 30 days";
  }
  if (dataSourceType === "defillama") {
    return "e.g. TVL history for Aave, or DEX volume overview";
  }
  if (dataSourceType === "dune") {
    return "Describe the Dune query you want (requires a query_id)";
  }
  return PROMPT_PLACEHOLDERS[syntax] || PROMPT_PLACEHOLDERS.sql;
}

export default function QueryPromptLine({
  className,
  dataSourceId,
  dataSourceType,
  dataSourceName,
  syntax,
  schema,
  existingQuery,
  disabled,
  onGenerated,
}) {
  const [prompt, setPrompt] = useState("");
  const [generating, setGenerating] = useState(false);

  const canGenerate = !disabled && !generating && !!dataSourceId && !!prompt.trim();

  const generateQuery = useCallback(async () => {
    const trimmedPrompt = prompt.trim();
    if (!trimmedPrompt || !dataSourceId || generating) {
      return;
    }

    setGenerating(true);
    try {
      const result = await Assistant.generateQuery({
        prompt: trimmedPrompt,
        dataSourceId,
        dataSourceType,
        dataSourceName,
        syntax,
        schema,
        existingQuery,
      });
      onGenerated(result.query);
      setPrompt("");
    } catch (error) {
      notification.error(get(error, "response.data.message", error.message || "Could not generate query."));
    } finally {
      setGenerating(false);
    }
  }, [
    prompt,
    dataSourceId,
    dataSourceType,
    dataSourceName,
    syntax,
    schema,
    existingQuery,
    generating,
    onGenerated,
  ]);

  const handleKeyDown = useCallback(
    event => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        if (canGenerate) {
          generateQuery();
        }
      }
    },
    [canGenerate, generateQuery]
  );

  return (
    <div className={cx("query-prompt-line", className)} data-test="QueryPromptLine">
      <label className="query-prompt-line__label" htmlFor="query-prompt-input">
        Describe
      </label>
      <input
        id="query-prompt-input"
        className="query-prompt-line__input"
        type="text"
        value={prompt}
        disabled={disabled || generating}
        placeholder={promptPlaceholder(syntax, dataSourceType)}
        onChange={event => setPrompt(event.target.value)}
        onKeyDown={handleKeyDown}
      />
      <Tooltip title={canGenerate ? "Generate query (Enter)" : "Describe your query first"}>
        <button
          type="button"
          className="query-prompt-line__action"
          disabled={!canGenerate}
          aria-label="Generate query from description"
          onClick={generateQuery}>
          {generating ? <LoadingOutlined spin /> : <ThunderboltOutlined />}
        </button>
      </Tooltip>
    </div>
  );
}

QueryPromptLine.propTypes = {
  className: PropTypes.string,
  dataSourceId: PropTypes.number,
  dataSourceType: PropTypes.string,
  dataSourceName: PropTypes.string,
  syntax: PropTypes.string,
  schema: PropTypes.array, // eslint-disable-line react/forbid-prop-types
  existingQuery: PropTypes.string,
  disabled: PropTypes.bool,
  onGenerated: PropTypes.func.isRequired,
};

QueryPromptLine.defaultProps = {
  className: null,
  dataSourceId: null,
  dataSourceType: null,
  dataSourceName: null,
  syntax: null,
  schema: [],
  existingQuery: null,
  disabled: false,
};
