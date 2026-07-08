import { map, isEmpty } from "lodash";
import React from "react";
import cx from "classnames";

import routeWithUserSession from "@/components/ApplicationArea/routeWithUserSession";
import Link from "@/components/Link";
import Paginator from "@/components/Paginator";
import DynamicComponent from "@/components/DynamicComponent";
import { DashboardTagsControl } from "@/components/tags-control/TagsControl";
import { wrap as itemsList, ControllerType } from "@/components/items-list/ItemsList";
import { ResourceItemsSource } from "@/components/items-list/classes/ItemsSource";
import { UrlStateStorage } from "@/components/items-list/classes/StateStorage";
import * as Sidebar from "@/components/items-list/components/Sidebar";
import ListPageToolbar from "@/components/items-list/components/ListPageToolbar";
import ItemsTable, { Columns } from "@/components/items-list/components/ItemsTable";
import useItemsListExtraActions from "@/components/items-list/hooks/useItemsListExtraActions";

import { Dashboard } from "@/services/dashboard";
import { currentUser } from "@/services/auth";
import getTags from "@/services/getTags";
import notification from "@/services/notification";
import { policy } from "@/services/policy";
import routes from "@/services/routes";
import DashboardThumbnail from "@/components/dashboards/DashboardThumbnail";

import DashboardListEmptyState from "./components/DashboardListEmptyState";

import "./dashboard-list.css";

const sidebarMenu = [
  {
    key: "all",
    href: "dashboards",
    title: "All Dashboards",
    icon: () => <Sidebar.MenuIcon icon="zmdi zmdi-view-quilt" />,
  },
  {
    key: "my",
    href: "dashboards/my",
    title: "My Dashboards",
    icon: () => <Sidebar.ProfileImage user={currentUser} />,
  },
  {
    key: "favorites",
    href: "dashboards/favorites",
    title: "Favorites",
    icon: () => <Sidebar.MenuIcon icon="fa fa-star" />,
  },
];

function getDashboardTags() {
  return getTags("api/dashboards/tags").then(tags => map(tags, t => t.name));
}

function buildColumns(refresh) {
  return [
    Columns.favorites({ className: "p-r-0" }),
    Columns.custom.sortable(
      (text, item) => (
        <div className={cx("dashboard-list-item", { "dashboard-list-item--no-tags": isEmpty(item.tags) })}>
          <DashboardThumbnail dashboardId={item.id} alt={item.name} size="list" />
          <div className="dashboard-list-item__details">
            <Link className="table-main-title" href={item.url} data-test={`DashboardId${item.id}`}>
              {item.name}
            </Link>
            <DashboardTagsControl
              className="d-block"
              tags={item.tags}
              isDraft={item.is_draft}
              isArchived={item.is_archived}
              canEdit={!item.is_archived && policy.canEdit(item)}
              getAvailableTags={getDashboardTags}
              onEdit={tags =>
                Dashboard.save({ id: item.id, tags, version: item.version })
                  .then(() => refresh())
                  .catch(() => notification.error("Failed to update tags."))
              }
            />
          </div>
        </div>
      ),
      {
        title: "Name",
        field: "name",
        width: null,
      }
    ),
    Columns.custom((text, item) => item.user.name, { title: "Created By", width: "1%" }),
    Columns.dateTime.sortable({
      title: "Created At",
      field: "created_at",
      width: "1%",
    }),
  ];
}

function DashboardListExtraActions(props) {
  return <DynamicComponent name="DashboardList.Actions" {...props} />;
}

function DashboardList({ controller }) {
  let usedListColumns = buildColumns(() => controller.update());
  if (controller.params.currentPage === "favorites") {
    usedListColumns = [
      ...usedListColumns,
      Columns.dateTime.sortable({ title: "Starred At", field: "starred_at", width: "1%" }),
    ];
  }
  const {
    areExtraActionsAvailable,
    listColumns: tableColumns,
    Component: ExtraActionsComponent,
    selectedItems,
  } = useItemsListExtraActions(controller, usedListColumns, DashboardListExtraActions);

  return (
    <div className="page-dashboard-list">
      <div className="container">
        <ListPageToolbar
          searchPlaceholder="Search Dashboards..."
          searchLabel="Search dashboards"
          searchValue={controller.searchTerm}
          onSearchChange={controller.updateSearch}
          menu={sidebarMenu}
          selected={controller.params.currentPage}
          tagsUrl="api/dashboards/tags"
          onTagsChange={controller.updateSelectedTags}
          selectedTags={controller.selectedTags}
        />
        <div className="list-page-layout__content">
          <div data-test="DashboardLayoutContent">
            {controller.isLoaded && controller.isEmpty ? (
              <DashboardListEmptyState
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
                    onPageSizeChange={(itemsPerPage) => controller.updatePagination({ itemsPerPage })}
                    page={controller.page}
                    onChange={(page) => controller.updatePagination({ page })}
                  />
                </div>
              </React.Fragment>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

DashboardList.propTypes = {
  controller: ControllerType.isRequired,
};

const DashboardListPage = itemsList(
  DashboardList,
  () =>
    new ResourceItemsSource({
      getResource({ params: { currentPage } }) {
        return {
          all: Dashboard.query.bind(Dashboard),
          my: Dashboard.myDashboards.bind(Dashboard),
          favorites: Dashboard.favorites.bind(Dashboard),
        }[currentPage];
      },
      getItemProcessor() {
        return (item) => new Dashboard(item);
      },
    }),
  ({ ...props }) => new UrlStateStorage({ orderByField: props.orderByField ?? "created_at", orderByReverse: true })
);

routes.register(
  "Dashboards.List",
  routeWithUserSession({
    path: "/dashboards",
    title: "Dashboards",
    render: (pageProps) => <DashboardListPage {...pageProps} currentPage="all" />,
  })
);
routes.register(
  "Dashboards.Favorites",
  routeWithUserSession({
    path: "/dashboards/favorites",
    title: "Favorite Dashboards",
    render: (pageProps) => <DashboardListPage {...pageProps} currentPage="favorites" orderByField="starred_at" />,
  })
);
routes.register(
  "Dashboards.My",
  routeWithUserSession({
    path: "/dashboards/my",
    title: "My Dashboards",
    render: (pageProps) => <DashboardListPage {...pageProps} currentPage="my" />,
  })
);
