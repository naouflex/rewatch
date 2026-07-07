import React from "react";
import PropTypes from "prop-types";
import cx from "classnames";

import "./SettingsSection.less";

export default function SettingsSection({ title, description, children, className, helpTrigger }) {
  return (
    <section className={cx("settings-section", className)}>
      {(title || description || helpTrigger) && (
        <header className="settings-section__header">
          <div className="settings-section__heading">
            {title && <h3 className="settings-section__title">{title}</h3>}
            {description && <p className="settings-section__desc">{description}</p>}
          </div>
          {helpTrigger}
        </header>
      )}
      <div className="settings-section__body">{children}</div>
    </section>
  );
}

SettingsSection.propTypes = {
  title: PropTypes.node,
  description: PropTypes.string,
  children: PropTypes.node,
  className: PropTypes.string,
  helpTrigger: PropTypes.node,
};

SettingsSection.defaultProps = {
  title: null,
  description: null,
  children: null,
  className: null,
  helpTrigger: null,
};
