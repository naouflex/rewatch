import React from "react";
import PropTypes from "prop-types";

import Link from "@/components/Link";
import PageHeader from "@/components/PageHeader";

import "./create-page-layout.less";

export default function CreatePageLayout({ backHref, backLabel, title, children, actions }) {
  return (
    <>
      {backHref && (
        <div className="create-page-form__back">
          <Link href={backHref}>
            <i className="fa fa-angle-left m-r-5" aria-hidden="true" />
            {backLabel}
          </Link>
        </div>
      )}
      {title && <PageHeader title={title} actions={actions} />}
      {children}
    </>
  );
}

CreatePageLayout.propTypes = {
  backHref: PropTypes.string,
  backLabel: PropTypes.string,
  title: PropTypes.string,
  children: PropTypes.node,
  actions: PropTypes.node,
};

CreatePageLayout.defaultProps = {
  backHref: null,
  backLabel: "Back",
  title: null,
  children: null,
  actions: null,
};
