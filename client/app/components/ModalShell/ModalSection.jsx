import React from "react";
import PropTypes from "prop-types";
import cx from "classnames";

export default function ModalSection({ title, description, children, className }) {
  return (
    <section className={cx("modal-shell__section", className)}>
      {(title || description) && (
        <header className="modal-shell__section-header">
          {title && <h4 className="modal-shell__section-title">{title}</h4>}
          {description && <p className="modal-shell__section-desc">{description}</p>}
        </header>
      )}
      <div className="modal-shell__section-body">{children}</div>
    </section>
  );
}

ModalSection.propTypes = {
  title: PropTypes.node,
  description: PropTypes.string,
  children: PropTypes.node,
  className: PropTypes.string,
};

ModalSection.defaultProps = {
  title: null,
  description: null,
  children: null,
  className: null,
};
