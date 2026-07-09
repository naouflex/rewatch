import React from "react";
import PropTypes from "prop-types";
import cx from "classnames";

import "./ConfigSection.less";

export default function ConfigSection({ title, action, children, className, bordered, help }) {
  return (
    <section className={cx("config-section", className, { "config-section--bordered": bordered })}>
      {(title || action) && (
        <div className="config-section__header">
          {title && <h4 className="config-section__title">{title}</h4>}
          {action && <div className="config-section__action">{action}</div>}
        </div>
      )}
      {help && <p className="config-section__help">{help}</p>}
      <div className="config-section__body">{children}</div>
    </section>
  );
}

ConfigSection.propTypes = {
  title: PropTypes.node,
  action: PropTypes.node,
  children: PropTypes.node,
  className: PropTypes.string,
  bordered: PropTypes.bool,
  help: PropTypes.node,
};

ConfigSection.defaultProps = {
  title: null,
  action: null,
  children: null,
  className: null,
  bordered: true,
  help: null,
};
