import { map } from "lodash";
import React from "react";

import Modal from "antd/lib/modal";

import routeWithUserSession from "@/components/ApplicationArea/routeWithUserSession";
import Link from "@/components/Link";
import Paginator from "@/components/Paginator";
import Tooltip from "@/components/Tooltip";
import PlainButton from "@/components/PlainButton";
import { DestinationTagsControl } from "@/components/tags-control/TagsControl";

import { wrap as itemsList, ControllerType } from "@/components/items-list/ItemsList";
import { ResourceItemsSource } from "@/components/items-list/classes/ItemsSource";
import { UrlStateStorage } from "@/components/items-list/classes/StateStorage";

import * as Sidebar from "@/components/items-list/components/Sidebar";
import ListPageToolbar from "@/components/items-list/components/ListPageToolbar";
import ItemsTable, { Columns } from "@/components/items-list/components/ItemsTable";

import DestinationService, { Destination, IMG_ROOT } from "@/services/destination";
import { currentUser } from "@/services/auth";
import getTags from "@/services/getTags";
import location from "@/services/location";
import notification from "@/services/notification";
import routes from "@/services/routes";

function getDestinationTags() {
  return getTags("api/destinations/tags").then(tags => map(tags, t => t.name));
}

const sidebarMenu = [
  {
    key: "all",
    href: "destinations",
    title: "All Destinations",
    icon: () => <Sidebar.MenuIcon icon="fa fa-paper-plane-o" />,
  },
  {
    key: "my",
    href: "destinations/my",
    title: "My Destinations",
    icon: () => <Sidebar.ProfileImage user={currentUser} />,
    isAvailable: () => currentUser.hasPermission("list_destinations"),
  },
  {
    key: "favorites",
    href: "destinations/favorites",
    title: "Favorites",
    icon: () => <Sidebar.MenuIcon icon="fa fa-star" />,
  },
  {
    key: "archive",
    href: "destinations/archive",
    title: "Archived",
    icon: () => <Sidebar.MenuIcon icon="fa fa-archive" />,
  },
];

function canModify(destination) {
  return currentUser.isAdmin || currentUser.id === destination.user_id;
}

function archiveDestination(destination, onSuccess) {
  Modal.confirm({
    title: `Archive "${destination.name}"?`,
    content: "Archived destinations are hidden from the default list but can be restored later.",
    okText: "Archive",
    okType: "danger",
    onOk: () =>
      DestinationService.doArchive(destination)
        .then(() => {
          notification.success("Alert destination archived.");
          onSuccess();
        })
        .catch(() => notification.error("Failed to archive alert destination.")),
  });
}

function deleteDestination(destination, onSuccess) {
  Modal.confirm({
    title: `Delete "${destination.name}"?`,
    content: "Are you sure you want to delete this alert destination?",
    okText: "Delete",
    okType: "danger",
    onOk: () =>
      DestinationService.delete(destination)
        .then(() => {
          notification.success("Alert destination deleted successfully.");
          onSuccess();
        })
        .catch(() => notification.error("Failed to delete alert destination.")),
  });
}

function buildColumns(refresh) {
  return [
    Columns.favorites({ className: "p-r-0" }),
    Columns.custom.sortable(
      (text, destination) => (
        <React.Fragment>
          <Link className="table-main-title" href={`destinations/${destination.id}`}>
            <img
              src={`${IMG_ROOT}/${destination.type}.png`}
              className="m-r-5"
              width="20"
              alt={destination.type}
            />
            {destination.name}
          </Link>
          <DestinationTagsControl
            className="d-block"
            tags={destination.tags}
            isArchived={destination.is_archived}
            canEdit={canModify(destination)}
            getAvailableTags={getDestinationTags}
            onEdit={tags =>
              DestinationService.save({ id: destination.id, tags })
                .then(() => refresh())
                .catch(() => notification.error("Failed to update tags."))
            }
          />
        </React.Fragment>
      ),
      {
        title: "Name",
        field: "name",
      }
    ),
    Columns.custom.sortable((text, destination) => destination.type, {
      title: "Type",
      field: "type",
      width: "1%",
      className: "text-nowrap",
    }),
    Columns.custom((text, item) => (item.user ? item.user.name : ""), {
      title: "Created By",
      width: "1%",
    }),
    Columns.dateTime.sortable({ title: "Created At", field: "created_at", width: "1%" }),
    Columns.custom(
      (text, destination) => {
        if (!canModify(destination) || destination.is_archived) {
          return null;
        }
        return (
          <Tooltip title="Archive">
            <PlainButton onClick={() => archiveDestination(destination, refresh)}>
              <i className="fa fa-archive" aria-hidden="true" />
              <span className="sr-only">archive</span>
            </PlainButton>
          </Tooltip>
        );
      },
      { title: "", width: "1%" }
    ),
    Columns.custom(
      (text, destination) => {
        if (!canModify(destination)) {
          return null;
        }
        return (
          <Tooltip title="Delete">
            <PlainButton onClick={() => deleteDestination(destination, refresh)}>
              <i className="fa fa-trash" aria-hidden="true" />
              <span className="sr-only">delete</span>
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
      return "You don't have any alert destinations yet.";
    case "favorites":
      return "You haven't marked any alert destination as favorite yet.";
    case "archive":
      return "No alert destinations have been archived.";
    default:
      return "There are no alert destinations yet.";
  }
}

class DestinationsList extends React.Component {
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
    const columns = buildColumns(() => controller.update());

    return (
      <div className="page-destinations-list">
        <div className="container">
          <ListPageToolbar
            searchPlaceholder="Search Destinations..."
            searchLabel="Search destinations"
            searchValue={controller.searchTerm}
            onSearchChange={controller.updateSearch}
            menu={sidebarMenu}
            selected={currentPage}
            tagsUrl="api/destinations/tags"
            onTagsChange={controller.updateSelectedTags}
            selectedTags={controller.selectedTags}
          />
          <div className="list-page-layout__content">
            {controller.isLoaded && controller.isEmpty ? (
              <div className="text-center bg-white tiled p-30">
                <i className="fa fa-paper-plane-o f-30 text-muted" aria-hidden="true" />
                <p className="m-t-10 text-muted">{emptyStateContentFor(currentPage)}</p>
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
                  onPageSizeChange={itemsPerPage => controller.updatePagination({ itemsPerPage })}
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

const DestinationsListPage = itemsList(
  DestinationsList,
  () =>
    new ResourceItemsSource({
      isPlainList: true,
      getRequest() {
        return {};
      },
      getResource({ params: { currentPage } }) {
        return {
          all: DestinationService.query.bind(DestinationService),
          my: DestinationService.myDestinations.bind(DestinationService),
          favorites: DestinationService.favorites.bind(DestinationService),
          archive: DestinationService.archive.bind(DestinationService),
        }[currentPage];
      },
      getItemProcessor() {
        return item => new Destination(item);
      },
    }),
  () => new UrlStateStorage({ orderByField: "created_at", orderByReverse: true, itemsPerPage: 20 })
);

routes.register(
  "AlertDestinations.List",
  routeWithUserSession({
    path: "/destinations",
    title: "Alert Destinations",
    render: pageProps => <DestinationsListPage {...pageProps} currentPage="all" />,
  })
);
routes.register(
  "AlertDestinations.My",
  routeWithUserSession({
    path: "/destinations/my",
    title: "My Alert Destinations",
    render: pageProps => <DestinationsListPage {...pageProps} currentPage="my" />,
  })
);
routes.register(
  "AlertDestinations.Favorites",
  routeWithUserSession({
    path: "/destinations/favorites",
    title: "Favorite Alert Destinations",
    render: pageProps => <DestinationsListPage {...pageProps} currentPage="favorites" />,
  })
);
routes.register(
  "AlertDestinations.Archived",
  routeWithUserSession({
    path: "/destinations/archive",
    title: "Archived Alert Destinations",
    render: pageProps => <DestinationsListPage {...pageProps} currentPage="archive" />,
  })
);
