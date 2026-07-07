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

import { MLModel } from "@/services/ml-model";
import { currentUser } from "@/services/auth";
import location from "@/services/location";
import routes from "@/services/routes";

import MLModelListEmptyState from "./MLModelListEmptyState";

import "./models-list.less";
import { MLModelTagsControl } from "@/components/tags-control/TagsControl";
import { FIXED_TABLE_WIDTHS as W } from "@/components/items-list/fixedTableWidths";

export const STATE_CLASS = {
  unknown: "label-warning",
  ok: "label-success",
  triggered: "label-danger",
  training: "label-info",
  trained: "label-success",
  predicting: "label-info",
  predicted: "label-success",
  error: "label-danger",
};

const sidebarMenu = [
  {
    key: "all",
    href: "ml_models",
    title: "All Models",
    icon: () => <Sidebar.MenuIcon icon="fa fa-cubes" />,
  },
  {
    key: "my",
    href: "ml_models/my",
    title: "My Models",
    icon: () => <Sidebar.ProfileImage user={currentUser} />,
  },
  {
    key: "favorites",
    href: "ml_models/favorites",
    title: "Favorites",
    icon: () => <Sidebar.MenuIcon icon="fa fa-star" />,
  },
  {
    key: "archive",
    href: "ml_models/archive",
    title: "Archived",
    icon: () => <Sidebar.MenuIcon icon="fa fa-archive" />,
  },
];

const listColumns = [
  Columns.favorites({ className: "p-r-0", width: W.favorite }),
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
      width: W.icon,
    }
  ),
  Columns.custom.sortable(
    (text, model) => (
      <div className="list-page-table__cell-stack">
        <Link className="table-main-title" href={"ml_models/" + model.id + "/overview"} title={model.name}>
          {model.name}
        </Link>
        <MLModelTagsControl className="d-block" tags={model.tags} isArchived={model.is_archived} />
      </div>
    ),
    {
      title: "Name",
      field: "name",
      ellipsis: true,
    }
  ),
  Columns.custom.sortable(
    (text, model) =>
      model.query ? (
        <Link href={"queries/" + model.query.id} className="list-page-table__truncate" title={model.query.name}>
          {model.query.name}
        </Link>
      ) : (
        "No query"
      ),
    {
      title: "Query",
      field: "query.name",
      ellipsis: true,
      width: W.query,
    }
  ),
  Columns.custom((text, item) => (item.user ? item.user.name : ""), {
    title: "Created By",
    width: W.author,
    ellipsis: true,
  }),
  Columns.custom.sortable(
    (text, item) => (
      <span className={`label ${STATE_CLASS[item.state_train]}`}>{toUpper(item.state_train)}</span>
    ),
    {
      title: "Training",
      field: "state_train",
      width: W.stateLabel,
      className: "text-nowrap",
    }
  ),
  Columns.custom.sortable(
    (text, item) => (
      <span className={`label ${STATE_CLASS[item.state_predict]}`}>{toUpper(item.state_predict)}</span>
    ),
    {
      title: "Predicting",
      field: "state_predict",
      width: W.stateLabel,
      className: "text-nowrap",
    }
  ),
  Columns.timeAgo.sortable({ title: "Last Updated", field: "updated_at", width: W.timeAgo }),
  Columns.dateTime.sortable({ title: "Created At", field: "created_at", width: W.dateTime }),
];

function MLModelsListExtraActions(props) {
  return <DynamicComponent name="MLModelsList.Actions" {...props} />;
}

function MLModelsList({ controller }) {
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
          searchLabel="Search models"
          searchValue={controller.searchTerm}
          onSearchChange={controller.updateSearch}
          menu={sidebarMenu}
          selected={controller.params.currentPage}
          tagsUrl="api/ml_models/tags"
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

MLModelsList.propTypes = {
  controller: ControllerType.isRequired,
};

const MLMLModelsListPage = itemsList(
  MLModelsList,
  () =>
    new ResourceItemsSource({
      getResource({ params: { currentPage } }) {
        return {
          all: MLModel.query.bind(MLModel),
          my: MLModel.myModels.bind(MLModel),
          favorites: MLModel.favorites.bind(MLModel),
          archive: MLModel.archive.bind(MLModel),
        }[currentPage];
      },
      getItemProcessor() {
        return item => new MLModel(item);
      },
    }),
  () => new UrlStateStorage({ orderByField: "created_at", orderByReverse: true, itemsPerPage: 100 })
);

routes.register(
  "MLModels.List",
  routeWithUserSession({
    path: "/ml_models",
    title: "Models",
    render: pageProps => <MLMLModelsListPage {...pageProps} currentPage="all" />,
  })
);
routes.register(
  "MLModels.Favorites",
  routeWithUserSession({
    path: "/ml_models/favorites",
    title: "Favorite Models",
    render: pageProps => <MLMLModelsListPage {...pageProps} currentPage="favorites" />,
  })
);
routes.register(
  "MLModels.Archive",
  routeWithUserSession({
    path: "/ml_models/archive",
    title: "Archived Models",
    render: pageProps => <MLMLModelsListPage {...pageProps} currentPage="archive" />,
  })
);
routes.register(
  "MLModels.My",
  routeWithUserSession({
    path: "/ml_models/my",
    title: "My Models",
    render: pageProps => <MLMLModelsListPage {...pageProps} currentPage="my" />,
  })
);
