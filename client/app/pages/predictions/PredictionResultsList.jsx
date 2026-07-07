import React, { useEffect, useRef } from "react";
import cx from "classnames";
import routeWithUserSession from "../../components/ApplicationArea/routeWithUserSession";
import Link from "@/components/Link";
import Paginator from "@/components/Paginator";
import DynamicComponent from "@/components/DynamicComponent";

import { wrap as itemsList, ControllerType } from "@/components/items-list/ItemsList";
import useItemsListExtraActions from "@/components/items-list/hooks/useItemsListExtraActions";
import { ResourceItemsSource } from "@/components/items-list/classes/ItemsSource";
import { UrlStateStorage } from "@/components/items-list/classes/StateStorage";

import * as Sidebar from "@/components/items-list/components/Sidebar";
import ListPageToolbar from "@/components/items-list/components/ListPageToolbar";
import ItemsTable, { Columns } from "@/components/items-list/components/ItemsTable";

import { CheckCircleOutlined, CloseCircleOutlined, InfoCircleOutlined } from '@ant-design/icons';
import Tooltip from "antd/lib/tooltip"

import { PredictionResult } from "@/services/prediction";
import { currentUser } from "@/services/auth";
import location from "@/services/location";
import routes from "@/services/routes";

import PredictionResultsListEmptyState from "./PredictionResultsListEmptyState";

import "./predictions-list.css";
import { FIXED_TABLE_WIDTHS as W } from "@/components/items-list/fixedTableWidths";

function getPredictionSummary(item) {
  const props = item.additional_properties || {};
  const overall = props.overall || {};
  if (overall.r2_score !== undefined && overall.r2_score !== null) {
    return `R² ${Number(overall.r2_score).toFixed(4)}`;
  }
  if (overall.is_overfitted !== undefined) {
    return overall.is_overfitted ? "Overfitted" : "Not overfitted";
  }
  const rows = item.content && item.content.rows;
  if (Array.isArray(rows)) {
    return `${rows.length} rows`;
  }
  return "View details";
}

const listColumns = [
  Columns.favorites({ className: "p-r-0", width: W.favorite }),
  Columns.custom.sortable(
    (text, item) => {
      const label = item.model && item.model.name ? item.model.name : `Prediction #${item.id}`;
      return (
        <Link href={"predictions/" + item.id} className="table-main-title list-page-table__truncate" title={label}>
          {label}
        </Link>
      );
    },
    { title: "Model", field: "model.name", ellipsis: true }
  ),
  Columns.custom(
    (text, item) => {
      let icon;
      let color;
      if (item.status === "success") {
        icon = <CheckCircleOutlined style={{ color: "green" }} />;
        color = "green";
      } else if (item.status === "error") {
        icon = <CloseCircleOutlined style={{ color: "red" }} />;
        color = "red";
      } else {
        icon = <InfoCircleOutlined style={{ color: "blue" }} />;
        color = "blue";
      }
      return (
        <Tooltip title={item.status || "unknown"}>
          <span style={{ color }} className="text-nowrap">
            {icon} {item.status || "unknown"}
          </span>
        </Tooltip>
      );
    },
    { title: "Status", field: "status", width: W.status, className: "text-nowrap" }
  ),
  Columns.custom(
    (text, item) => (
      <span className="text-muted list-page-table__truncate" title={getPredictionSummary(item)}>
        {getPredictionSummary(item)}
      </span>
    ),
    { title: "Summary", ellipsis: true, width: W.summary }
  ),
  Columns.custom(
    (text, item) => (item.model_version ? `v${item.model_version}` : "—"),
    { title: "Version", field: "model_version", width: W.version, className: "text-nowrap" }
  ),
  Columns.timeAgo.sortable({ title: "Created", field: "created_at", width: W.timeAgo }),
];

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
        <ListPageToolbar
          searchPlaceholder="Search Predictions..."
          searchLabel="Search predictions"
          searchValue={controller.searchTerm}
          onSearchChange={controller.updateSearch}
          menu={sidebarMenu}
          selected={controller.params.currentPage}
          tagsUrl="api/predictions/tags"
          onTagsChange={controller.updateSelectedTags}
          selectedTags={controller.selectedTags}
        />
        <div className="list-page-layout__content">
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
              <div className="list-page-table list-page-table--fixed">
                <ItemsTable
                  items={controller.pageItems}
                  loading={!controller.isLoaded}
                  columns={tableColumns}
                  tableLayout="fixed"
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
        </div>
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
