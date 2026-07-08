import { isEmpty, keyBy, take } from "lodash";
import React, { useCallback, useEffect, useState } from "react";
import PropTypes from "prop-types";

import Button from "antd/lib/button";
import BigMessage from "@/components/BigMessage";
import Link from "@/components/Link";
import Paginator from "@/components/Paginator";
import TimeAgo from "@/components/TimeAgo";
import CreateDashboardDialog from "@/components/dashboards/CreateDashboardDialog";
import DashboardThumbnail from "@/components/dashboards/DashboardThumbnail";
import { QuerySourceTypeIcon } from "@/pages/queries/components/QuerySourceTypeIcon";
import { currentUser } from "@/services/auth";
import DataSource from "@/services/data-source";
import { Dashboard } from "@/services/dashboard";
import { Query } from "@/services/query";

import HomeSection, { HomeListItem, HomeListSkeleton } from "./HomeSection";

const QUERIES_PANEL_PAGE_SIZE = 6;
const DASHBOARDS_PANEL_PAGE_SIZE = 6;
const FAVORITES_PANEL_LIMIT = 3;

function DraftBadge() {
  return <span className="label label-default home-list-item__badge">Unpublished</span>;
}

function FavoriteSublist({ title, resource, itemUrl, viewAllHref, emptyState, showThumbnail, showDataSourceIcon }) {
  const [items, setItems] = useState([]);
  const [dataSourcesById, setDataSourcesById] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const favoritesPromise = resource.favorites({ order: "-starred_at" });
    const dataSourcesPromise = showDataSourceIcon ? DataSource.query() : Promise.resolve([]);

    Promise.all([favoritesPromise, dataSourcesPromise])
      .then(([favoritesResult, dataSources]) => {
        setItems(take(favoritesResult.results, FAVORITES_PANEL_LIMIT));
        if (showDataSourceIcon) {
          setDataSourcesById(keyBy(dataSources, "id"));
        }
      })
      .finally(() => setLoading(false));
  }, [resource, showDataSourceIcon]);

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
      {loading && <HomeListSkeleton rows={FAVORITES_PANEL_LIMIT} compact />}
      {!loading && !isEmpty(items) && (
        <div role="list" className="home-list home-list--compact">
          {items.map(item => {
            const dataSource = showDataSourceIcon ? dataSourcesById[item.data_source_id] : null;

            return (
            <HomeListItem
              key={itemUrl(item)}
              href={itemUrl(item)}
              className="home-list-item--compact"
              thumbnail={
                showThumbnail ? (
                  <DashboardThumbnail dashboardId={item.id} alt={item.name} size="home" />
                ) : null
              }
              icon={
                showThumbnail ? null : showDataSourceIcon ? (
                  dataSource ? (
                    <QuerySourceTypeIcon dataSource={dataSource} alt={dataSource.name} width={20} height={20} />
                  ) : (
                    <i className="fa fa-code home-list-item__fallback-icon" aria-hidden="true" />
                  )
                ) : (
                  <span className="btn-favorite home-list-item__star" aria-hidden="true">
                    <i className="fa fa-star" />
                  </span>
                )
              }
              title={
                <>
                  {(showThumbnail || showDataSourceIcon) && (
                    <i className="fa fa-star home-list-item__favorite-mark" aria-hidden="true" />
                  )}
                  {item.name}
                </>
              }
              meta={
                item.updated_at ? (
                  <>
                    Updated <TimeAgo date={item.updated_at} />
                  </>
                ) : null
              }
              badge={item.is_draft ? <DraftBadge /> : null}
            />
            );
          })}
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
  showThumbnail: PropTypes.bool,
  showDataSourceIcon: PropTypes.bool,
};

FavoriteSublist.defaultProps = {
  viewAllHref: null,
  emptyState: null,
  showThumbnail: false,
  showDataSourceIcon: false,
};

function RecentQueriesList() {
  const [queries, setQueries] = useState([]);
  const [dataSourcesById, setDataSourcesById] = useState({});
  const [loading, setLoading] = useState(true);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  const loadQueries = useCallback((nextPage = 1) => {
    setLoading(true);
    const queriesPromise = Query.myQueries({
      page: nextPage,
      page_size: QUERIES_PANEL_PAGE_SIZE,
      order: "-updated_at",
    });
    const dataSourcesPromise = hasLoaded ? Promise.resolve(null) : DataSource.query();

    Promise.all([queriesPromise, dataSourcesPromise])
      .then(([queriesResult, dataSources]) => {
        setQueries(queriesResult.results);
        setTotalCount(queriesResult.count);
        setPage(nextPage);
        if (dataSources) {
          setDataSourcesById(keyBy(dataSources, "id"));
        }
      })
      .finally(() => {
        setLoading(false);
        setHasLoaded(true);
      });
  }, [hasLoaded]);

  useEffect(() => {
    loadQueries(1);
  }, [loadQueries]);

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
      loading={loading && !hasLoaded}
      compact
      skeletonRows={QUERIES_PANEL_PAGE_SIZE}
      className="home-workspace-row__panel"
    >
      {!isEmpty(queries) && (
        <>
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
                  badge={query.is_draft ? <DraftBadge /> : null}
                />
              );
            })}
          </div>
          <Paginator
            page={page}
            pageSize={QUERIES_PANEL_PAGE_SIZE}
            totalCount={totalCount}
            onChange={loadQueries}
            size="small"
            simple
          />
        </>
      )}
      {isEmpty(queries) && !loading && emptyState}
    </HomeSection>
  );
}

function RecentDashboardsList() {
  const [dashboards, setDashboards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  const loadDashboards = useCallback((nextPage = 1) => {
    setLoading(true);
    Dashboard.myDashboards({ page: nextPage, page_size: DASHBOARDS_PANEL_PAGE_SIZE, order: "-updated_at" })
      .then(({ results, count }) => {
        setDashboards(results);
        setTotalCount(count);
        setPage(nextPage);
      })
      .finally(() => {
        setLoading(false);
        setHasLoaded(true);
      });
  }, []);

  useEffect(() => {
    loadDashboards(1);
  }, [loadDashboards]);

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
      loading={loading && !hasLoaded}
      compact
      skeletonRows={DASHBOARDS_PANEL_PAGE_SIZE}
      className="home-workspace-row__panel"
    >
      {!isEmpty(dashboards) && (
        <>
          <div role="list" className="home-list home-list--compact">
            {dashboards.map(dashboard => (
              <HomeListItem
                key={dashboard.id}
                href={dashboard.url}
                className="home-list-item--compact"
                thumbnail={<DashboardThumbnail dashboardId={dashboard.id} alt={dashboard.name} size="home" />}
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
          <Paginator
            page={page}
            pageSize={DASHBOARDS_PANEL_PAGE_SIZE}
            totalCount={totalCount}
            onChange={loadDashboards}
            size="small"
            simple
          />
        </>
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
        showThumbnail
      />
      <FavoriteSublist
        title="Queries"
        resource={Query}
        itemUrl={query => `queries/${query.id}`}
        viewAllHref="queries/favorites"
        emptyState={queryEmptyState}
        showDataSourceIcon
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
