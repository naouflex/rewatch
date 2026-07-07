import React from "react";
import PropTypes from "prop-types";

import "./index.less";

export default function PageHeader({ title, description, actions }) {
  return (
    <div className="page-header-wrapper">
      <div className="page-header-main">
        <h3>{title}</h3>
        {description && <div className="page-header-description">{description}</div>}
      </div>
      {actions && <div className="page-header-actions">{actions}</div>}
    </div>
  );
}

PageHeader.propTypes = {
  title: PropTypes.string,
  description: PropTypes.node,
  actions: PropTypes.node,
};

PageHeader.defaultProps = {
  title: "",
  description: null,
  actions: null,
};
