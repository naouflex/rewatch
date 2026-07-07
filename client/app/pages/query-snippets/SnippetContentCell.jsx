import React, { useState } from "react";
import PropTypes from "prop-types";
import cx from "classnames";
import PlainButton from "@/components/PlainButton";

const EXPAND_THRESHOLD = 120;

export default function SnippetContentCell({ content }) {
  const [expanded, setExpanded] = useState(false);
  const canExpand = (content || "").length > EXPAND_THRESHOLD;

  return (
    <div className="snippet-content-cell">
      <code
        className={cx("snippet-content", {
          "snippet-content--expanded": expanded,
          "snippet-content--clamped": !expanded && canExpand,
        })}>
        {content}
      </code>
      {canExpand && (
        <PlainButton type="link" className="snippet-content-cell__toggle" onClick={() => setExpanded(v => !v)}>
          {expanded ? "Show less" : "Show more"}
        </PlainButton>
      )}
    </div>
  );
}

SnippetContentCell.propTypes = {
  content: PropTypes.string,
};

SnippetContentCell.defaultProps = {
  content: "",
};
