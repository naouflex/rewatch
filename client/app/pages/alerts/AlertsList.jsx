import React from "react";
import cx from "classnames";
import { toUpper } from "lodash";

import Modal from "antd/lib/modal";

import routeWithUserSession from "@/components/ApplicationArea/routeWithUserSession";
import Link from "@/components/Link";
import Paginator from "@/components/Paginator";
import EmptyState, { EmptyStateHelpMessage } from "@/components/empty-state/EmptyState";
import DynamicComponent from "@/components/DynamicComponent";
import Tooltip from "@/components/Tooltip";
import PlainButton from "@/components/PlainButton";
import notification from "@/services/notification";

import { wrap as itemsList, ControllerType } from "@/components/items-list/ItemsList";
import { ResourceItemsSource } from "@/components/items-list/classes/ItemsSource";
import { UrlStateStorage } from "@/components/items-list/classes/StateStorage";

import * as Sidebar from "@/components/items-list/components/Sidebar";
import ListPageToolbar from "@/components/items-list/components/ListPageToolbar";
import ItemsTable, { Columns } from "@/components/items-list/components/ItemsTable";

import { AlertTagsControl } from "@/components/tags-control/TagsControl";

import AlertService, { Alert } from "@/services/alert";
import { currentUser } from "@/services/auth";
import location from "@/services/location";
import routes from "@/services/routes";

export const STATE_CLASS = {
  unknown: "label-warning",
  ok: "label-success",
  triggered: "label-danger",
};

const sidebarMenu = [
  {
    key: "all",
    href: "alerts",
    title: "All Alerts",
    icon: () => <Sidebar.MenuIcon icon="fa fa-bell" />,
  },
  {
    key: "my",
    href: "alerts/my",
    title: "My Alerts",
    icon: () => <Sidebar.ProfileImage user={currentUser} />,
    isAvailable: () => currentUser.hasPermission("list_alerts"),
  },
  {
    key: "favorites",
    href: "alerts/favorites",
    title: "Favorites",
    icon: () => <Sidebar.MenuIcon icon="fa fa-star" />,
  },
  {
    key: "archive",
    href: "alerts/archive",
    title: "Archived",
    icon: () => <Sidebar.MenuIcon icon="fa fa-archive" />,
  },
];

function archiveAlert(alert, onSuccess) {
  Modal.confirm({
    title: `Archive "${alert.name}"?`,
    content: "Archived alerts no longer appear in the list and stop sending notifications.",
    okType: "danger",
    onOk: () =>
      AlertService.doArchive({ id: alert.id })
        .then(() => {
          notification.success("Alert archived.");
          onSuccess();
        })
        .catch(() => notification.error("Failed to archive alert.")),
  });
}

function buildColumns(currentPage, refresh) {
  return [
    Columns.favorites({ className: "p-r-0" }),
    Columns.custom.sortable(
      (text, alert) => (
        <span title={alert.options && alert.options.muted ? "Muted" : "Active"}>
          <i
            className={`fa fa-bell-${alert.options && alert.options.muted ? "slash" : "o"} p-r-0`}
            aria-hidden="true"
          />
          <span className="sr-only">{alert.options && alert.options.muted ? "Muted" : "Active"}</span>
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
    Columns.custom.sortable(
      (text, alert) => (
        <React.Fragment>
          <Link className="table-main-title" href={"alerts/" + alert.id}>
            {alert.name}
          </Link>
          <AlertTagsControl
            className="d-block"
            tags={alert.tags}
            isArchived={alert.is_archived}
          />
        </React.Fragment>
      ),
      {
        title: "Name",
        field: "name",
      }
    ),
    Columns.custom((text, item) => (item.user ? item.user.name : ""), {
      title: "Created By",
      width: "1%",
    }),
    Columns.custom.sortable(
      (text, alert) => (
        <span className={`label ${STATE_CLASS[alert.state]}`}>{toUpper(alert.state)}</span>
      ),
      {
        title: "State",
        field: "state",
        width: "1%",
        className: "text-nowrap",
      }
    ),
    Columns.timeAgo.sortable({ title: "Last Updated At", field: "updated_at", width: "1%" }),
    Columns.dateTime.sortable({ title: "Created At", field: "created_at", width: "1%" }),
    Columns.custom(
      (text, alert) => {
        const canArchive =
          currentPage !== "archive" &&
          (currentUser.isAdmin || (alert.user && currentUser.id === alert.user.id));
        if (!canArchive) {
          return null;
        }
        return (
          <Tooltip title="Archive">
            <PlainButton onClick={() => archiveAlert(alert, refresh)}>
              <i className="fa fa-archive" aria-hidden="true" />
              <span className="sr-only">archive</span>
            </PlainButton>
          </Tooltip>
        );
      },
      { title: "", width: "1%" }
    ),
  ];
}

function emptyStateContentFor(currentPage) {
  switch (currentPage) {
    case "my":
      return "You don't have any alerts yet.";
    case "favorites":
      return "You haven't marked any alert as favorite yet.";
    case "archive":
      return "No alerts have been archived.";
    default:
      return null;
  }
}

class AlertsList extends React.Component {
  static propTypes = {
    controller: ControllerType.isRequired,
  };

  componentDidMount() {
    const searchTerm = location.search.q || "";
    if (searchTerm && searchTerm !== this.props.controller.searchTerm) {
      this.props.controller.updateSearch(searchTerm);
    }
  }

  render() {
    const { controller } = this.props;
    const { currentPage } = controller.params;
    const columns = buildColumns(currentPage, () => controller.update());

    const customEmptyText = emptyStateContentFor(currentPage);

    return (
      <div className="page-alerts-list">
        <div className="container">
          <ListPageToolbar
            searchPlaceholder="Search Alerts..."
            searchLabel="Search alerts"
            searchValue={controller.searchTerm}
            onSearchChange={controller.updateSearch}
            menu={sidebarMenu}
            selected={currentPage}
            tagsUrl="api/alerts/tags"
            onTagsChange={controller.updateSelectedTags}
            selectedTags={controller.selectedTags}
          />
          <div className="list-page-layout__content">
            {controller.isLoaded && controller.isEmpty ? (
                <DynamicComponent name="AlertsList.EmptyState">
                  {customEmptyText ? (
                    <div className="text-center bg-white tiled p-30">
                      <i
                        className={cx("fa fa-bell-o text-muted", { "f-30": true })}
                        aria-hidden="true"
                      />
                      <p className="m-t-10 text-muted">{customEmptyText}</p>
                    </div>
                  ) : (
                    <EmptyState
                      icon="fa fa-bell-o"
                      illustration="alert"
                      description="Get notified on certain events"
                      helpMessage={<EmptyStateHelpMessage helpTriggerType="ALERTS" />}
                      showAlertStep
                    />
                  )}
                </DynamicComponent>
              ) : (
                <div className="list-page-table">
                  <ItemsTable
                    items={controller.pageItems}
                    loading={!controller.isLoaded}
                    columns={columns}
                    orderByField={controller.orderByField}
                    orderByReverse={controller.orderByReverse}
                    toggleSorting={controller.toggleSorting}
                  />
                  <Paginator
                    showPageSizeSelect
                    totalCount={controller.totalItemsCount}
                    pageSize={controller.itemsPerPage}
                    onPageSizeChange={itemsPerPage =>
                      controller.updatePagination({ itemsPerPage })
                    }
                    page={controller.page}
                    onChange={page => controller.updatePagination({ page })}
                  />
                </div>
              )}
          </div>
        </div>
      </div>
    );
  }
}

const AlertsListPage = itemsList(
  AlertsList,
  () =>
    new ResourceItemsSource({
      isPlainList: true,
      getRequest() {
        return {};
      },
      getResource({ params: { currentPage } }) {
        return {
          all: AlertService.query.bind(AlertService),
          my: AlertService.myAlerts.bind(AlertService),
          favorites: AlertService.favorites.bind(AlertService),
          archive: AlertService.archive.bind(AlertService),
        }[currentPage];
      },
      getItemProcessor() {
        return item => new Alert(item);
      },
    }),
  () => new UrlStateStorage({ orderByField: "created_at", orderByReverse: true, itemsPerPage: 20 })
);

routes.register(
  "Alerts.List",
  routeWithUserSession({
    path: "/alerts",
    title: "Alerts",
    render: pageProps => <AlertsListPage {...pageProps} currentPage="all" />,
  })
);
routes.register(
  "Alerts.My",
  routeWithUserSession({
    path: "/alerts/my",
    title: "My Alerts",
    render: pageProps => <AlertsListPage {...pageProps} currentPage="my" />,
  })
);
routes.register(
  "Alerts.Favorites",
  routeWithUserSession({
    path: "/alerts/favorites",
    title: "Favorite Alerts",
    render: pageProps => <AlertsListPage {...pageProps} currentPage="favorites" />,
  })
);
routes.register(
  "Alerts.Archived",
  routeWithUserSession({
    path: "/alerts/archive",
    title: "Archived Alerts",
    render: pageProps => <AlertsListPage {...pageProps} currentPage="archive" />,
  })
);
