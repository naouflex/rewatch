import React from "react";
import { get } from "lodash";

import Tag from "antd/lib/tag";

import routeWithUserSession from "@/components/ApplicationArea/routeWithUserSession";
import Link from "@/components/Link";
import Paginator from "@/components/Paginator";
import Tooltip from "@/components/Tooltip";
import PlainButton from "@/components/PlainButton";
import NotificationContentModal from "@/components/alerts/NotificationContentModal";
import { confirmDialog } from "@/components/ModalShell/confirmDialog";

import { wrap as itemsList, ControllerType } from "@/components/items-list/ItemsList";
import { ItemsSource } from "@/components/items-list/classes/ItemsSource";
import { UrlStateStorage } from "@/components/items-list/classes/StateStorage";

import * as Sidebar from "@/components/items-list/components/Sidebar";
import ListPageToolbar from "@/components/items-list/components/ListPageToolbar";
import ItemsTable, { Columns } from "@/components/items-list/components/ItemsTable";
import TimeAgo from "@/components/TimeAgo";

import AlertEvents from "@/services/alert-events";
import { destinationLabel, statusTag } from "@/pages/alert-events/alertEventUtils";
import { currentUser } from "@/services/auth";
import notification from "@/services/notification";
import routes from "@/services/routes";

const STATE_COLORS = {
  ok: "green",
  triggered: "red",
  unknown: "orange",
};

const sidebarMenu = [
  {
    key: "all",
    href: "alert_events",
    title: "All Events",
    icon: () => <Sidebar.MenuIcon icon="fa fa-history" />,
  },
  {
    key: "archive",
    href: "alert_events/archive",
    title: "Archived",
    icon: () => <Sidebar.MenuIcon icon="fa fa-archive" />,
  },
];

function stateTag(state) {
  if (!state) {
    return null;
  }
  return <Tag color={STATE_COLORS[state] || "default"}>{state.toUpperCase()}</Tag>;
}

class AlertEventsList extends React.Component {
  static propTypes = {
    controller: ControllerType.isRequired,
  };

  state = {
    selectedEvent: null,
  };

  buildColumns(currentPage) {
    const isManager = currentUser.isAdmin;
    const refresh = () => this.props.controller.update();

    return [
      Columns.custom(
        (text, event) => <TimeAgo date={event.created_at} variation="timeAgoInTooltip" />,
        {
          title: "Date",
          field: "created_at",
          width: "1%",
          className: "text-nowrap",
        }
      ),
      Columns.custom(
        (text, event) =>
          event.alert ? (
            <Link href={`alerts/${event.alert.id}`}>{event.alert.name}</Link>
          ) : (
            "—"
          ),
        { title: "Alert", field: "alert" }
      ),
      Columns.custom((text, event) => statusTag(event.status), {
        title: "Status",
        width: "1%",
      }),
      Columns.custom((text, event) => stateTag(event.state), {
        title: "State",
        width: "1%",
      }),
      Columns.custom((text, event) => destinationLabel(event), {
        title: "Destination",
        width: "1%",
      }),
      Columns.custom(
        (text, event) =>
          event.row_index !== null && event.row_index !== undefined ? `#${event.row_index}` : "—",
        { title: "Row", width: "1%", className: "text-nowrap" }
      ),
      Columns.custom(
        (text, event) => (
          <span className="d-flex">
            <Tooltip title="View notification content">
              <PlainButton
                className="m-r-5"
                onClick={() => this.setState({ selectedEvent: event })}>
                <i className="fa fa-eye" aria-hidden="true" />
                <span className="sr-only">View</span>
              </PlainButton>
            </Tooltip>
            {isManager && currentPage !== "archive" && (
              <Tooltip title="Archive">
                <PlainButton
                  className="m-r-5"
                  onClick={() => this.archiveEvent(event, refresh)}>
                  <i className="fa fa-archive" aria-hidden="true" />
                  <span className="sr-only">Archive</span>
                </PlainButton>
              </Tooltip>
            )}
            {isManager && (
              <Tooltip title="Delete">
                <PlainButton onClick={() => this.deleteEvent(event, refresh)}>
                  <i className="fa fa-trash text-danger" aria-hidden="true" />
                  <span className="sr-only">Delete</span>
                </PlainButton>
              </Tooltip>
            )}
          </span>
        ),
        { title: "", width: "1%" }
      ),
    ];
  }

  archiveEvent(event, onSuccess) {
    if (!event.alert) {
      return;
    }
    confirmDialog({
      title: "Archive this event?",
      description: "Archived events are hidden from the default views.",
      onConfirm: () =>
        AlertEvents.archive({ alertId: event.alert.id, eventId: event.id })
          .then(() => {
            notification.success("Event archived.");
            onSuccess();
          })
          .catch(() => notification.error("Failed to archive event.")),
    });
  }

  deleteEvent(event, onSuccess) {
    if (!event.alert) {
      return;
    }
    confirmDialog({
      title: "Delete this event?",
      variant: "danger",
      description: "This will permanently remove the event from history.",
      onConfirm: () =>
        AlertEvents.delete({ alertId: event.alert.id, eventId: event.id })
          .then(() => {
            notification.success("Event deleted.");
            onSuccess();
          })
          .catch(() => notification.error("Failed to delete event.")),
    });
  }

  renderModal() {
    const { selectedEvent } = this.state;
    return (
      <NotificationContentModal
        open={!!selectedEvent}
        event={selectedEvent}
        onClose={() => this.setState({ selectedEvent: null })}
      />
    );
  }

  render() {
    const { controller } = this.props;
    const { currentPage } = controller.params;
    const columns = this.buildColumns(currentPage);

    return (
      <div className="page-alert-events-list">
        <div className="container">
          <ListPageToolbar
            searchPlaceholder="Search events..."
            searchLabel="Search alert events"
            searchValue={controller.searchTerm}
            onSearchChange={controller.updateSearch}
            menu={sidebarMenu}
            selected={currentPage}
          />
          <div className="list-page-layout__content">
            {controller.isLoaded && controller.isEmpty ? (
              <div className="text-center bg-white tiled p-30">
                <i className="fa fa-history text-muted f-30" aria-hidden="true" />
                <p className="m-t-10 text-muted">
                  {currentPage === "archive"
                    ? "No archived alert events."
                    : "No alert notifications have been recorded yet."}
                </p>
              </div>
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
        {this.renderModal()}
      </div>
    );
  }
}

const AlertEventsListPage = itemsList(
  AlertEventsList,
  () =>
    new ItemsSource({
      isPlainList: true,
      getRequest(request, { params: { currentPage } }) {
        return {
          q: request.q,
          include_archived: currentPage === "archive",
          limit: 500,
        };
      },
      doRequest(request) {
        return AlertEvents.feed({
          includeArchived: request.include_archived,
          limit: request.limit,
        }).then(events => {
          if (!request.q) {
            return events;
          }
          const needle = request.q.toLowerCase();
          return events.filter(event => {
            const haystack = [
              get(event, "alert.name", ""),
              event.content || "",
              destinationLabel(event),
              event.state || "",
              event.status || "",
            ]
              .join(" ")
              .toLowerCase();
            return haystack.indexOf(needle) !== -1;
          });
        });
      },
    }),
  () => new UrlStateStorage({ orderByField: "created_at", orderByReverse: true, itemsPerPage: 20 })
);

routes.register(
  "AlertEvents.List",
  routeWithUserSession({
    path: "/alert_events",
    title: "Alerts History",
    render: pageProps => <AlertEventsListPage {...pageProps} currentPage="all" />,
  })
);
routes.register(
  "AlertEvents.Archived",
  routeWithUserSession({
    path: "/alert_events/archive",
    title: "Archived Alert Events",
    render: pageProps => <AlertEventsListPage {...pageProps} currentPage="archive" />,
  })
);
