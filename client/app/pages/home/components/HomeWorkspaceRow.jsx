import { isEmpty, keyBy, orderBy, take } from "lodash";
import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";

import Button from "antd/lib/button";
import BigMessage from "@/components/BigMessage";
import Link from "@/components/Link";
import TimeAgo from "@/components/TimeAgo";
import CreateDashboardDialog from "@/components/dashboards/CreateDashboardDialog";
import { QuerySourceTypeIcon } from "@/pages/queries/components/QuerySourceTypeIcon";
import { currentUser } from "@/services/auth";
import DataSource from "@/services/data-source";
import { Dashboard } from "@/services/dashboard";
import { Query } from "@/services/query";

import HomeSection, { HomeListItem, HomeListSkeleton } from "./HomeSection";

const ITEM_LIMIT = 3;

function DraftBadge() {
  return <span className="label label-default home-list-item__badge">Unpublished</span>;
}

function FavoriteSublist({ title, resource, itemUrl, viewAllHref, emptyState }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    resource
      .favorites({ order: "-starred_at" })
      .then(({ results }) => setItems(take(results, ITEM_LIMIT)))
      .finally(() => setLoading(false));
  }, [resource]);

  return (
    <div className="home-favorites-sublist">
      <div className="home-favorites-sublist__header">
        <p className="home-favorites-sublist__title">{title}</p>
        {!loading && !isEmpty(items) && viewAllHref && (
          <Link className="home-section__view-all" href={viewAllHref}>
            View all
          </Link>
        )}
      </div>
      {loading && <HomeListSkeleton rows={ITEM_LIMIT} compact />}
      {!loading && !isEmpty(items) && (
        <div role="list" className="home-list home-list--compact">
          {items.map(item => (
            <HomeListItem
              key={itemUrl(item)}
              href={itemUrl(item)}
              className="home-list-item--compact"
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
              badge={item.is_draft ? <DraftBadge /> : null}
            />
          ))}
        </div>
      )}
      {isEmpty(items) && !loading && emptyState}
    </div>
  );
}

FavoriteSublist.propTypes = {
  title: PropTypes.string.isRequired,
  resource: PropTypes.func.isRequired, // eslint-disable-line react/forbid-prop-types
  itemUrl: PropTypes.func.isRequired,
  viewAllHref: PropTypes.string,
  emptyState: PropTypes.node,
};

FavoriteSublist.defaultProps = {
  viewAllHref: null,
  emptyState: null,
};

function RecentQueriesList() {
  const [queries, setQueries] = useState([]);
  const [dataSourcesById, setDataSourcesById] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([Query.recent(), DataSource.query()])
      .then(([recentQueries, dataSources]) => {
        const published = recentQueries.filter(query => !query.is_draft);
        setQueries(take(published, ITEM_LIMIT));
        setDataSourcesById(keyBy(dataSources, "id"));
      })
      .finally(() => setLoading(false));
  }, []);

  const emptyState = currentUser.hasPermission("create_query") ? (
    <BigMessage icon="fa-code" className="home-section-empty home-section-empty--compact">
      <Link.Button href="queries/new" type="primary" size="small">
        New query
      </Link.Button>
    </BigMessage>
  ) : (
    <BigMessage message="No recent queries." icon="fa-code" className="home-section-empty home-section-empty--compact" />
  );

  return (
    <HomeSection
      title="Recently edited queries"
      viewAllHref="queries/my"
      loading={loading}
      compact
      skeletonRows={ITEM_LIMIT}
      className="home-workspace-row__panel"
    >
      {!isEmpty(queries) && (
        <div role="list" className="home-list home-list--compact">
          {queries.map(query => {
            const dataSource = dataSourcesById[query.data_source_id];
            return (
              <HomeListItem
                key={query.id}
                href={`queries/${query.id}`}
                className="home-list-item--compact"
                icon={
                  dataSource ? (
                    <QuerySourceTypeIcon dataSource={dataSource} alt={dataSource.name} width={20} height={20} />
                  ) : (
                    <i className="fa fa-code home-list-item__fallback-icon" aria-hidden="true" />
                  )
                }
                title={query.name}
                meta={
                  <>
                    Edited <TimeAgo date={query.updated_at} />
                  </>
                }
              />
            );
          })}
        </div>
      )}
      {isEmpty(queries) && !loading && emptyState}
    </HomeSection>
  );
}

function RecentDashboardsList() {
  const [dashboards, setDashboards] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Dashboard.myDashboards({ page_size: ITEM_LIMIT })
      .then(({ results }) => {
        setDashboards(take(orderBy(results, item => item.updated_at, "desc"), ITEM_LIMIT));
      })
      .finally(() => setLoading(false));
  }, []);

  const emptyState = currentUser.hasPermission("create_dashboard") ? (
    <BigMessage icon="zmdi zmdi-view-quilt" className="home-section-empty home-section-empty--compact">
      <Button type="primary" size="small" onClick={() => CreateDashboardDialog.showModal()}>
        New dashboard
      </Button>
    </BigMessage>
  ) : (
    <BigMessage message="No dashboards yet." icon="zmdi zmdi-view-quilt" className="home-section-empty home-section-empty--compact" />
  );

  return (
    <HomeSection
      title="My dashboards"
      viewAllHref="dashboards/my"
      loading={loading}
      compact
      skeletonRows={ITEM_LIMIT}
      className="home-workspace-row__panel"
    >
      {!isEmpty(dashboards) && (
        <div role="list" className="home-list home-list--compact">
          {dashboards.map(dashboard => (
            <HomeListItem
              key={dashboard.id}
              href={dashboard.url}
              className="home-list-item--compact"
              icon={<i className="zmdi zmdi-view-quilt home-list-item__fallback-icon" aria-hidden="true" />}
              title={dashboard.name}
              meta={
                <>
                  Updated <TimeAgo date={dashboard.updated_at} />
                </>
              }
              badge={dashboard.is_draft ? <DraftBadge /> : null}
            />
          ))}
        </div>
      )}
      {isEmpty(dashboards) && !loading && emptyState}
    </HomeSection>
  );
}

function FavoritesPanel() {
  const dashboardEmptyState = (
    <BigMessage
      message="Star a dashboard to list it here."
      icon="fa-star"
      className="home-section-empty home-section-empty--compact"
    />
  );

  const queryEmptyState = (
    <BigMessage
      message="Star a query to list it here."
      icon="fa-star"
      className="home-section-empty home-section-empty--compact"
    />
  );

  return (
    <HomeSection title="Favorites" compact className="home-workspace-row__panel home-workspace-row__panel--favorites">
      <FavoriteSublist
        title="Dashboards"
        resource={Dashboard}
        itemUrl={dashboard => dashboard.url}
        viewAllHref="dashboards/favorites"
        emptyState={dashboardEmptyState}
      />
      <FavoriteSublist
        title="Queries"
        resource={Query}
        itemUrl={query => `queries/${query.id}`}
        viewAllHref="queries/favorites"
        emptyState={queryEmptyState}
      />
    </HomeSection>
  );
}

export default function HomeWorkspaceRow() {
  return (
    <div className="home-workspace-row">
      <RecentQueriesList />
      <RecentDashboardsList />
      <FavoritesPanel />
    </div>
  );
}
