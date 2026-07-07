import React from "react";
import PropTypes from "prop-types";
import classNames from "classnames";

import PlainButton from "@/components/PlainButton";

export default function ForumLikeButton({ count, isLiked, onToggle, disabled, size = "default" }) {
  return (
    <PlainButton
      type="link"
      className={classNames("forum-like-button", {
        "forum-like-button--active": isLiked,
        "forum-like-button--small": size === "small",
      })}
      disabled={disabled}
      onClick={onToggle}
    >
      <i className={`fa fa-thumbs-${isLiked ? "up" : "o-up"}`} aria-hidden="true" />
      <span>{count || 0}</span>
      <span className="sr-only">{isLiked ? "Unlike" : "Like"}</span>
    </PlainButton>
  );
}

ForumLikeButton.propTypes = {
  count: PropTypes.number,
  isLiked: PropTypes.bool,
  onToggle: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
  size: PropTypes.oneOf(["default", "small"]),
};

ForumLikeButton.defaultProps = {
  count: 0,
  isLiked: false,
  disabled: false,
  size: "default",
};
