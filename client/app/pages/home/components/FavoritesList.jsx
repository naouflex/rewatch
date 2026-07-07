import { isEmpty } from "lodash";
import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";

import Button from "antd/lib/button";
import BigMessage from "@/components/BigMessage";
import Link from "@/components/Link";
import TimeAgo from "@/components/TimeAgo";
import CreateDashboardDialog from "@/components/dashboards/CreateDashboardDialog";
import HelpTrigger from "@/components/HelpTrigger";
import { currentUser } from "@/services/auth";
import { Dashboard } from "@/services/dashboard";
import { Query } from "@/services/query";

import { HomeListItem, HomeListSkeleton } from "./HomeSection";

function FavoriteList({ title, resource, itemUrl, viewAllHref, emptyState }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    resource
      .favorites({ order: "-starred_at" })
      .then(({ results }) => setItems(results))
      .finally(() => setLoading(false));
  }, [resource]);

  return (
    <div className="home-favorites-column">
      <div className="home-favorites-column__header">
        <p className="home-favorites-column__title">{title}</p>
        {!loading && !isEmpty(items) && viewAllHref && (
          <Link className="home-section__view-all" href={viewAllHref}>
            View all
          </Link>
        )}
      </div>
      {loading && <HomeListSkeleton rows={3} />}
      {!loading && !isEmpty(items) && (
        <div role="list" className="home-list">
          {items.map((item) => (
            <HomeListItem
              key={itemUrl(item)}
              href={itemUrl(item)}
              icon={
                <span className="btn-favorite home-list-item__star" aria-hidden="true">
                  <i className="fa fa-star" />
                </span>
              }
              title={item.name}
              meta={
                item.updated_at ? (
                  <>
                    Updated <TimeAgo date={item.updated_at} />
                  </>
                ) : null
              }
              badge={item.is_draft ? <span className="label label-default home-list-item__badge">Unpublished</span> : null}
            />
          ))}
        </div>
      )}
      {isEmpty(items) && !loading && emptyState}
    </div>
  );
}

FavoriteList.propTypes = {
  title: PropTypes.string.isRequired,
  resource: PropTypes.func.isRequired, // eslint-disable-line react/forbid-prop-types
  itemUrl: PropTypes.func.isRequired,
  viewAllHref: PropTypes.string,
  emptyState: PropTypes.node,
};

FavoriteList.defaultProps = {
  viewAllHref: null,
  emptyState: null,
};

export function DashboardAndQueryFavoritesList() {
  const dashboardEmptyState = currentUser.hasPermission("create_dashboard") ? (
    <BigMessage icon="fa-star" className="home-section-empty home-section-empty--compact">
      <span>
        <Button type="primary" size="small" onClick={() => CreateDashboardDialog.showModal()}>
          Create a dashboard
        </Button>{" "}
        or star one from <Link href="dashboards">Dashboards</Link>
      </span>
    </BigMessage>
  ) : (
    <BigMessage
      message="Mark dashboards as favorite to list them here."
      icon="fa-star"
      className="home-section-empty home-section-empty--compact"
    />
  );

  const queryEmptyState = currentUser.hasPermission("create_query") ? (
    <BigMessage icon="fa-star" className="home-section-empty home-section-empty--compact">
      <span>
        <Link.Button href="queries/new" type="primary" size="small">
          Create a query
        </Link.Button>{" "}
        or star one from <Link href="queries">Queries</Link>
      </span>
    </BigMessage>
  ) : (
    <BigMessage
      message="Mark queries as favorite to list them here."
      icon="fa-star"
      className="home-section-empty home-section-empty--compact"
    />
  );

  return (
    <div className="tile home-favorites">
      <div className="t-header home-section__header">
        <div className="th-title">Favorites</div>
      </div>
      <div className="t-body tb-padding">
        <div className="row home-favorites-list">
          <div className="col-sm-6">
            <FavoriteList
              title="Dashboards"
              resource={Dashboard}
              itemUrl={(dashboard) => dashboard.url}
              viewAllHref="dashboards/favorites"
              emptyState={dashboardEmptyState}
            />
          </div>
          <div className="col-sm-6">
            <FavoriteList
              title="Queries"
              resource={Query}
              itemUrl={(query) => `queries/${query.id}`}
              viewAllHref="queries/favorites"
              emptyState={queryEmptyState}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
