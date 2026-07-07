import { isEmpty, keyBy, orderBy, take } from "lodash";
import React, { useEffect, useState } from "react";

import Button from "antd/lib/button";
import BigMessage from "@/components/BigMessage";
import Link from "@/components/Link";
import TimeAgo from "@/components/TimeAgo";
import CreateDashboardDialog from "@/components/dashboards/CreateDashboardDialog";
import HelpTrigger from "@/components/HelpTrigger";
import { QuerySourceTypeIcon } from "@/pages/queries/components/QuerySourceTypeIcon";
import { currentUser } from "@/services/auth";
import DataSource from "@/services/data-source";
import { Dashboard } from "@/services/dashboard";
import { Query } from "@/services/query";

import HomeSection, { HomeListItem } from "./HomeSection";

const ITEM_LIMIT = 6;

function DraftBadge() {
  return <span className="label label-default home-list-item__badge">Unpublished</span>;
}

function RecentQueriesList() {
  const [queries, setQueries] = useState([]);
  const [dataSourcesById, setDataSourcesById] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([Query.recent(), DataSource.query()])
      .then(([recentQueries, dataSources]) => {
        const published = recentQueries.filter((query) => !query.is_draft);
        setQueries(take(published, ITEM_LIMIT));
        setDataSourcesById(keyBy(dataSources, "id"));
      })
      .finally(() => setLoading(false));
  }, []);

  const emptyState = currentUser.hasPermission("create_query") ? (
    <BigMessage icon="fa-code" className="home-section-empty">
      <span>
        <Link.Button href="queries/new" type="primary" size="small">
          Create your first query
        </Link.Button>{" "}
        <HelpTrigger className="f-13" type="QUERIES" showTooltip={false}>
          Need help?
        </HelpTrigger>
      </span>
    </BigMessage>
  ) : (
    <BigMessage message="No recent queries yet." icon="fa-code" className="home-section-empty" />
  );

  return (
    <HomeSection title="Recently edited queries" viewAllHref="queries/my" loading={loading}>
      {!isEmpty(queries) && (
        <div role="list" className="home-list">
          {queries.map((query) => {
            const dataSource = dataSourcesById[query.data_source_id];
            return (
              <HomeListItem
                key={query.id}
                href={`queries/${query.id}`}
                icon={
                  dataSource ? (
                    <QuerySourceTypeIcon dataSource={dataSource} alt={dataSource.name} width={24} height={24} />
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
        setDashboards(take(orderBy(results, (item) => item.updated_at, "desc"), ITEM_LIMIT));
      })
      .finally(() => setLoading(false));
  }, []);

  const emptyState = currentUser.hasPermission("create_dashboard") ? (
    <BigMessage icon="zmdi zmdi-view-quilt" className="home-section-empty">
      <span>
        <Button type="primary" size="small" onClick={() => CreateDashboardDialog.showModal()}>
          Create your first dashboard
        </Button>{" "}
        <HelpTrigger className="f-13" type="DASHBOARDS" showTooltip={false}>
          Need help?
        </HelpTrigger>
      </span>
    </BigMessage>
  ) : (
    <BigMessage message="No dashboards yet." icon="zmdi zmdi-view-quilt" className="home-section-empty" />
  );

  return (
    <HomeSection title="My dashboards" viewAllHref="dashboards/my" loading={loading}>
      {!isEmpty(dashboards) && (
        <div role="list" className="home-list">
          {dashboards.map((dashboard) => (
            <HomeListItem
              key={dashboard.id}
              href={dashboard.url}
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

export default function RecentItemsRow() {
  return (
    <div className="row home-recent-row">
      <div className="col-md-6">
        <RecentQueriesList />
      </div>
      <div className="col-md-6">
        <RecentDashboardsList />
      </div>
    </div>
  );
}
