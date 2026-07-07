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

import { toUpper } from "lodash";

import { MLModelVersion } from "@/services/ml-models-versions";
import { currentUser } from "@/services/auth";
import location from "@/services/location";
import routes from "@/services/routes";

import MLModelListEmptyState from "./MLModelsVersionsListEmptyState";

import "./models-versions-list.css";
import { MLModelsVersionsTagsControl } from "@/components/tags-control/TagsControl";

import {STATE_CLASS} from "../ml-models/MLModelsList";

// Add this helper function at the top of the file
function formatDuration(seconds) {
  if (!seconds) return 'N/A';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = seconds % 60;
  return [
    hours > 0 ? `${hours}h` : null,
    minutes > 0 ? `${minutes}m` : null,
    `${remainingSeconds}s`
  ].filter(Boolean).join(' ');
}

const formatDate = (date) => {
  if (!date) return 'N/A';
  return new Intl.DateTimeFormat('en-GB', {
    year: '2-digit', 
    month: '2-digit', 
    day: '2-digit', 
    hour: '2-digit', 
    minute: '2-digit'
  }).format(new Date(date)).replace(/,/g, '');
};

const sidebarMenu = [
  {
    key: "all",
    href: "ml_models_versions",
    title: "All Models",
    icon: () => <Sidebar.MenuIcon icon="fa fa-cubes" />,
  },
  {
    key: "my",
    href: "ml_models_versions/my",
    title: "My Models",
    icon: () => <Sidebar.ProfileImage user={currentUser} />,
  },
  {
    key: "favorites",
    href: "ml_models_versions/favorites",
    title: "Favorites",
    icon: () => <Sidebar.MenuIcon icon="fa fa-star" />,
  },
  {
    key: "archive",
    href: "ml_models_versions/archive",
    title: "Archived",
    icon: () => <Sidebar.MenuIcon icon="fa fa-archive" />,
  },
];

const listColumns = [
  Columns.favorites({ className: "p-r-0" }),
  Columns.custom.sortable(
    (text, model) => (
      <span title={model.options.muted ? "Muted" : "Active"}>
        <i className={`fa fa-bell-${model.options.muted ? "slash" : "o"} p-r-0`} aria-hidden="true" />
        <span className="sr-only">{model.options.muted ? "Muted" : "Active"}</span>
      </span>
    ),
    {
      title: (
        <>
          <i className="fa fa-bell p-r-0" aria-hidden="true" />
          <span className="sr-only">Sort by notification status.</span>
        </>
      ),
      field: "muted",
      width: "1%",
    }
  ),
  Columns.custom(
    (text, model) => (
      <div>
        <Link href={`ml_models/${model.id}/predictions`}>
          <i className="fa fa-history" aria-hidden="true" />
        </Link>
      </div>
    ),
    {
      title: (
        <>
          <i className="fa fa-history" aria-hidden="true" />
          <span className="sr-only">Model History</span>
        </>
      ),
      width: "1%",
    }
  ),
  Columns.custom(
    (text, model) => (
      <div>
        <Link href={`ml_models/${model.id}/stats`}>
          <i className="fa fa-bar-chart" aria-hidden="true" />
        </Link>
      </div>
    ),
    {
      title: (
        <>
          <i className="fa  fa-bar-chart" aria-hidden="true" />
          <span className="sr-only">Model Statistics</span>
        </>
      ),
      width: "1%",
    }
  ),
  Columns.custom.sortable(
    (text, model) => (
      <React.Fragment>
          <Link className="table-main-title" href={"ml_models_versions/" + model.id}>
            {model.name}
          </Link>
          <MLModelsVersionsTagsControl className="d-block" tags={model.tags} isArchived={model.is_archived} />
        </React.Fragment>
    ),
    {
      title: "Name",
      field: "name",
    }
  ),
  Columns.custom.sortable(
    (text, model) => (
      <React.Fragment>
          <Link className="table-main-title" href={"ml_models_versions/" + model.id}>
            v{model.version}
          </Link>
        </React.Fragment>
    ),
    {
      title: "Version",
      field: "version",
    }
  ),
  Columns.custom.sortable(
    (text, model) => (
      <div>
        {model.query 
          ? <>
              {formatDate(model.query.retrieved_at)}
            </>
          : 'No query'}
      </div>
    ),
    {
      title: "Last Retrieved At",
      field: "query.retrieved_at",
      width: "1%"
    }
  ),
  Columns.custom.sortable(
    (text, model) => (
      <div>
        {model.query 
          ? <Link href={"queries/" + model.query.id}>{model.query.name}</Link>
          : 'No query'}
      </div>
    ),
    {
      title: "Query",
      field: "query.name",
      width: "1%"
      
    }
  ),
  Columns.custom((text, item) => item.user.name, { title: "Created By", width: "1%" }),

  //state
  Columns.custom.sortable(
    (text, item) => (
      <div>
        <span className={`label ${STATE_CLASS[item.state]}`}>{toUpper(item.state)}</span>
      </div>
    ),
    {
      title: "State",
      field: "state",
      width: "1%",
      className: "text-nowrap",
    }
  ),
  //state_train
  Columns.custom.sortable(
    (text, item) => (
      <div>
        <span className={`label ${STATE_CLASS[item.state_train]}`}>{toUpper(item.state_train)}</span>
      </div>
    ),
    {
      title: "Training",
      field: "state_train",
      width: "1%",
      className: "text-nowrap",
    }
  ),
  //state_predict
  Columns.custom.sortable(
    (text, item) => (
      <div>
        <span className={`label ${STATE_CLASS[item.state_predict]}`}>{toUpper(item.state_predict)}</span>
      </div>
    ),
    {
      title: "Predicting",
      field: "state_predict",
      width: "1%",
      className: "text-nowrap",
    }
  ),
  Columns.custom.sortable(
    (text, item) => <div>{formatDate(item.created_at)}</div>,
    { title: "Created At", field: "created_at", width: "1%" }
  ),
  Columns.custom.sortable(
    (text, item) => <div>{formatDate(item.updated_at)}</div>,
    { title: "Last Updated At", field: "updated_at", width: "1%" }
  ),
  Columns.custom.sortable(
    (text, item) => (
      <div>
        {item.options.train_last_triggered_at && (
          <span title="Training Last Triggered">
            {formatDate(item.options.train_last_triggered_at)}
          </span>
        )}
      </div>
    ),
    {
      title: "Training Last Triggered",
      field: "options.train_last_triggered_at",
      width: "1%",
    }
  ),
  Columns.custom.sortable(
    (text, item) => (
      <div>
        {item.options.predict_last_triggered_at && (
          <span title="Predicting Last Triggered">
            {formatDate(item.options.predict_last_triggered_at)}
          </span>
        )}
      </div>
    ),
    {
      title: "Predicting Last Triggered",
      field: "options.predict_last_triggered_at",
      width: "1%",
    }
  ),
  Columns.custom.sortable(
    (text, item) => (
      <div>
        {item.options.train_duration !== undefined ? (
          <span title="Training Duration">
            {formatDuration(item.options.train_duration)}
          </span>
        ) : (
          'N/A'
        )}
      </div>
    ),
    {
      title: "Training Duration",
      field: "options.train_duration",
      width: "1%",
    }
  ),
];

function MLModelsListExtraActions(props) {
  return <DynamicComponent name="MLModelsList.Actions" {...props} />;
}

function MLModelsVersionsList({ controller }) {
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
  } = useItemsListExtraActions(controller, listColumns, MLModelsListExtraActions);

  return (
    <div className="page-models-list">
      <div className="container">
        <ListPageToolbar
          searchPlaceholder="Search Models..."
          searchLabel="Search model versions"
          searchValue={controller.searchTerm}
          onSearchChange={controller.updateSearch}
          menu={sidebarMenu}
          selected={controller.params.currentPage}
          tagsUrl="api/ml_models_versions/tags"
          onTagsChange={controller.updateSelectedTags}
          selectedTags={controller.selectedTags}
        />
        <div className="list-page-layout__content">
          {controller.isLoaded && controller.isEmpty ? (
            <MLModelListEmptyState
              page={controller.params.currentPage}
              searchTerm={controller.searchTerm}
              selectedTags={controller.selectedTags}
            />
          ) : (
            <React.Fragment>
              <div className={cx({ "m-b-10": areExtraActionsAvailable })}>
                <ExtraActionsComponent selectedItems={selectedItems} />
              </div>
              <div className="list-page-table">
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
        </div>
      </div>
    </div>
  );
}

MLModelsVersionsList.propTypes = {
  controller: ControllerType.isRequired,
};

const MLModelsVersionsListPage = itemsList(
  MLModelsVersionsList,
  () =>
    new ResourceItemsSource({
      getResource({ params: { currentPage } }) {
        return {
          all: MLModelVersion.query.bind(MLModelVersion),
          my: MLModelVersion.myModelsVersions.bind(MLModelVersion),
          favorites: MLModelVersion.favorites.bind(MLModelVersion),
          archive: MLModelVersion.archive.bind(MLModelVersion),
        }[currentPage];
      },
      getItemProcessor() {
        return item => new MLModelVersion(item);
      },
    }),
  () => new UrlStateStorage({ orderByField: "created_at", orderByReverse: true, itemsPerPage: 100 })
);

routes.register(
  "MLModelsVersions.List",
  routeWithUserSession({
    path: "/ml_models_versions",
    title: "Models Versions",
    render: pageProps => <MLModelsVersionsListPage {...pageProps} currentPage="all" />,
  })
);
routes.register(
  "MLModelsVersions.Favorites",
  routeWithUserSession({
    path: "/ml_models_versions/favorites",
    title: "Favorite Models Versions",
    render: pageProps => <MLModelsVersionsListPage {...pageProps} currentPage="favorites" />,
  })
);
routes.register(
  "MLModelsVersions.Archive",
  routeWithUserSession({
    path: "/ml_models_versions/archive",
    title: "Archived Models Versions",
    render: pageProps => <MLModelsVersionsListPage {...pageProps} currentPage="archive" />,
  })
);
routes.register(
  "MLModelsVersions.My",
  routeWithUserSession({
    path: "/ml_models_versions/my",
    title: "My Models Versions",
    render: pageProps => <MLModelsVersionsListPage {...pageProps} currentPage="my" />,
  })
);
