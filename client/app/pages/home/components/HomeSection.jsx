import React from "react";
import PropTypes from "prop-types";
import classNames from "classnames";
import Skeleton from "antd/lib/skeleton";

import Link from "@/components/Link";

export function HomeListSkeleton({ rows = 4, compact }) {
  return (
    <div className={classNames("home-list-skeleton", compact && "home-list-skeleton--compact")} aria-hidden="true">
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="home-list-skeleton__row">
          <Skeleton.Avatar active size={compact ? 20 : "small"} shape="square" />
          <Skeleton
            active
            title={{ width: "60%" }}
            paragraph={{ rows: compact ? 0 : 1, width: "40%" }}
          />
        </div>
      ))}
    </div>
  );
}

HomeListSkeleton.propTypes = {
  rows: PropTypes.number,
  compact: PropTypes.bool,
};

HomeListSkeleton.defaultProps = {
  compact: false,
};

export function HomeListItem({ href, icon, title, meta, badge, className }) {
  return (
    <Link className={classNames("home-list-item", className)} href={href}>
      {icon && <span className="home-list-item__icon">{icon}</span>}
      <span className="home-list-item__content">
        <span className="home-list-item__title">{title}</span>
        {meta && <span className="home-list-item__meta">{meta}</span>}
      </span>
      {badge}
    </Link>
  );
}

HomeListItem.propTypes = {
  href: PropTypes.string.isRequired,
  icon: PropTypes.node,
  title: PropTypes.node.isRequired,
  meta: PropTypes.node,
  badge: PropTypes.node,
  className: PropTypes.string,
};

HomeListItem.defaultProps = {
  icon: null,
  meta: null,
  badge: null,
  className: null,
};

export default function HomeSection({
  title,
  viewAllHref,
  viewAllLabel,
  loading,
  children,
  className,
  compact,
  skeletonRows,
}) {
  return (
    <div className={classNames("tile home-section", compact && "home-section--compact", className)}>
      <div className="t-header home-section__header">
        <div className="th-title">{title}</div>
        {viewAllHref && !loading && (
          <Link className="home-section__view-all" href={viewAllHref}>
            {viewAllLabel || "View all"}
          </Link>
        )}
      </div>
      <div className="t-body tb-padding home-section__body">
        {loading ? <HomeListSkeleton rows={skeletonRows} compact={compact} /> : children}
      </div>
    </div>
  );
}

HomeSection.propTypes = {
  title: PropTypes.string.isRequired,
  viewAllHref: PropTypes.string,
  viewAllLabel: PropTypes.string,
  loading: PropTypes.bool,
  children: PropTypes.node,
  className: PropTypes.string,
  compact: PropTypes.bool,
  skeletonRows: PropTypes.number,
};

HomeSection.defaultProps = {
  viewAllHref: null,
  viewAllLabel: null,
  loading: false,
  children: null,
  className: null,
  compact: false,
  skeletonRows: 4,
};
