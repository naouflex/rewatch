import React, { useEffect, useRef } from "react";
import cx from "classnames";
import routeWithUserSession from "../../components/ApplicationArea/routeWithUserSession";
import Link from "@/components/Link";
import PageHeader from "@/components/PageHeader";
import Paginator from "@/components/Paginator";
import DynamicComponent from "@/components/DynamicComponent";

import { wrap as itemsList, ControllerType } from "@/components/items-list/ItemsList";
import useItemsListExtraActions from "@/components/items-list/hooks/useItemsListExtraActions";
import { ResourceItemsSource } from "@/components/items-list/classes/ItemsSource";
import { UrlStateStorage } from "@/components/items-list/classes/StateStorage";

import * as Sidebar from "@/components/items-list/components/Sidebar";
import ItemsTable, { Columns } from "@/components/items-list/components/ItemsTable";

import { CheckCircleOutlined, CloseCircleOutlined, InfoCircleOutlined } from '@ant-design/icons';
import Tooltip from "antd/lib/tooltip"

import Layout from "@/components/layouts/ContentWithSidebar";

import { PredictionResult } from "@/services/prediction";
import { currentUser } from "@/services/auth";
import location from "@/services/location";
import routes from "@/services/routes";

import PredictionResultsListEmptyState from "./PredictionResultsListEmptyState";

import "./predictions-list.css";

import JsonViewInteractive from "@/components/json-view-interactive/JsonViewInteractive";

const sidebarMenu = [
  {
    key: "all",
    href: "predictions",
    title: "All Predictions",
    icon: () => <Sidebar.MenuIcon icon="fa fa-cubes" />,
  },
  {
    key: "my",
    href: "predictions/my",
    title: "My Predictions",
    icon: () => <Sidebar.ProfileImage user={currentUser} />,
  },
  {
    key: "favorites",
    href: "predictions/favorites",
    title: "Favorites Predictions",
    icon: () => <Sidebar.MenuIcon icon="fa fa-star" />,
  },
  {
    key: "archive",
    href: "predictions/archive",
    title: "Archived Predictions",
    icon: () => <Sidebar.MenuIcon icon="fa fa-archive" />,
  },
];

const listColumns = [
  Columns.favorites({ className: "p-r-0" }),
  Columns.custom(
    (text, item) => (
      <Link href={"predictions/" + item.id} className="table-main-title">
        {item.id}
      </Link>
    ),
    { title: "ID", field: "id", width: "1%" }
  ),
  
  Columns.dateTime.sortable({ title: "Created At", field: "created_at", width: "15%" }),
  Columns.custom(
    (text, item) => {
      let icon, color;
      if (item.status === 'success') {
        icon = <CheckCircleOutlined style={{ color: 'green' }} />;
        color = 'green';
      } else if (item.status === 'error') {
        icon = <CloseCircleOutlined style={{ color: 'red' }} />;
        color = 'red';
      } else {
        icon = <InfoCircleOutlined style={{ color: 'blue' }} />;
        color = 'blue';
      }
      return (
        <Tooltip title={item.status}>
          <span style={{ color }}>{icon} {item.status}</span>
        </Tooltip>
      );
    },
    { title: "Status", field: "status", width: "1%" }
  ),
  Columns.custom(
    (text, item) => item.query.name,
    { title: "Query", field: "query.name", width: "15%" }
  ),
  Columns.custom(
    (text, item) => item.model.name,
    { title: "Model", field: "model.name", width: "15%" }
  ),
  Columns.custom(
    (text, item) => {
      const content = typeof item.content === 'string' ? JSON.parse(item.content) : item.content;
      return (
        <div style={{ maxWidth: '300px', overflow: 'hidden' }}>
          <JsonViewInteractive value={content} />
        </div>
      );
    },
    { title: "Content Preview", field: "content", width: "30%" }
  ),
];

function PredictionResultsListExtraActions(props) {
  return <DynamicComponent name="PredictionResultsList.Actions" {...props} />;
}

function PredictionResultsList({ controller }) {
  const controllerRef = useRef();
  controllerRef.current = controller;

  useEffect(() => {
    const unlistenLocationChanges = location.listen((unused, action) => {
      const searchTerm = location.search.q || "";
      if (action === "PUSH" && searchTerm !== controllerRef.current.searchTerm) {
        controllerRef.current.updateSearch(searchTerm);
      }
    });

    return () => {
      unlistenLocationChanges();
    };
  }, []);

  const {
    areExtraActionsAvailable,
    listColumns: tableColumns,
    Component: ExtraActionsComponent,
    selectedItems,
  } = useItemsListExtraActions(controller, listColumns, PredictionResultsListExtraActions);

  return (
    <div className="page-predictions-list">
      <div className="container">
        <PageHeader
          title={controller.params.pageTitle}
          actions={
            currentUser.hasPermission("use_model") ? (
              <Link.Button block type="primary" href="ml_models/new">
                <i className="fa fa-plus m-r-5" aria-hidden="true" />
                New Model
              </Link.Button>
            ) : null
          }
        />
        <Layout>
          <Layout.Sidebar className="m-b-0">
            <Sidebar.SearchInput
              placeholder="Search Predictions..."
              label="Search predictions"
              value={controller.searchTerm}
              onChange={controller.updateSearch}
            />
            <Sidebar.Menu items={sidebarMenu} selected={controller.params.currentPage} />
            <Sidebar.Tags url="api/predictions/tags" onChange={controller.updateSelectedTags} showUnselectAll />
          </Layout.Sidebar>
          <Layout.Content>
            {controller.isLoaded && controller.isEmpty ? (
              <PredictionResultsListEmptyState
                page={controller.params.currentPage}
                searchTerm={controller.searchTerm}
                selectedTags={controller.selectedTags}
              />
            ) : (
              <React.Fragment>
                <div className={cx({ "m-b-10": areExtraActionsAvailable })}>
                  <ExtraActionsComponent selectedItems={selectedItems} />
                </div>
                <div className="bg-white tiled table-responsive">
                  <ItemsTable
                    items={controller.pageItems}
                    loading={!controller.isLoaded}
                    columns={tableColumns}
                    orderByField={controller.orderByField}
                    orderByReverse={controller.orderByReverse}
                    toggleSorting={controller.toggleSorting}
                  />
                  <Paginator
                    showPageSizeSelect
                    totalCount={controller.totalItemsCount}
                    pageSize={controller.itemsPerPage}
                    onPageSizeChange={itemsPerPage => controller.updatePagination({ itemsPerPage })}
                    page={controller.page}
                    onChange={page => controller.updatePagination({ page })}
                  />
                </div>
              </React.Fragment>
            )}
          </Layout.Content>
        </Layout>
      </div>
    </div>
  );
}

PredictionResultsList.propTypes = {
  controller: ControllerType.isRequired,
};

const PredictionResultsListPage = itemsList(
  PredictionResultsList,
  () =>
    new ResourceItemsSource({
      getResource({ params: { currentPage } }) {
        return {
          all: PredictionResult.query.bind(PredictionResult),
          my: PredictionResult.myPredictionResults.bind(PredictionResult),
          favorites: PredictionResult.favorites.bind(PredictionResult),
          archive: PredictionResult.archive.bind(PredictionResult),
        }[currentPage];
      },
      getItemProcessor() {
        return item => new PredictionResult(item);
      },
    }),
  () => new UrlStateStorage({ orderByField: "created_at", orderByReverse: true, itemsPerPage: 100 })
);

routes.register(
  "PredictionResults.List",
  routeWithUserSession({
    path: "/predictions",
    title: "Predictions",
    render: pageProps => <PredictionResultsListPage {...pageProps} currentPage="all" />,
  })
);
routes.register(
  "PredictionResults.Favorites",
  routeWithUserSession({
    path: "/predictions/favorites",
    title: "Favorite Predictions",
    render: pageProps => <PredictionResultsListPage {...pageProps} currentPage="favorites" />,
  })
);
routes.register(
  "PredictionResults.Archive",
  routeWithUserSession({
    path: "/predictions/archive",
    title: "Archived Predictions",
    render: pageProps => <PredictionResultsListPage {...pageProps} currentPage="archive" />,
  })
);
routes.register(
  "PredictionResults.My",
  routeWithUserSession({
    path: "/predictions/my",
    title: "My Predictions",
    render: pageProps => <PredictionResultsListPage {...pageProps} currentPage="my" />,
  })
);
