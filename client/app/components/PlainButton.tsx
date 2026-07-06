import classNames from "classnames";
import React from "react";

import "./PlainButton.less";

export interface PlainButtonProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "type"> {
  type?: "link" | "button";
}

const PlainButton = React.forwardRef<HTMLButtonElement, PlainButtonProps>(function PlainButton(
  { className, type, ...rest },
  ref
) {
  return (
    <button
      ref={ref}
      className={classNames("plain-button", "clickable", { "plain-button-link": type === "link" }, className)}
      type="button"
      {...rest}
    />
  );
});

export default PlainButton;
