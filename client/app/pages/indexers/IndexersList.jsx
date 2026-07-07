import React from "react";
import cx from "classnames";
import { get } from "lodash";

import routeWithUserSession from "@/components/ApplicationArea/routeWithUserSession";
import { confirmDialog } from "@/components/ModalShell/confirmDialog";
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

import IndexerService, { Indexer } from "@/services/indexer";
import { currentUser } from "@/services/auth";
import location from "@/services/location";
import routes from "@/services/routes";

import { IndexerTagsControl } from "@/components/tags-control/TagsControl";

const sidebarMenu = [
  {
    key: "all",
    href: "indexers",
    title: "All Indexers",
    icon: () => <Sidebar.MenuIcon icon="fa fa-database" />,
  },
  {
    key: "my",
    href: "indexers/my",
    title: "My Indexers",
    icon: () => <Sidebar.ProfileImage user={currentUser} />,
    isAvailable: () => currentUser.hasPermission("list_indexers"),
  },
  {
    key: "favorites",
    href: "indexers/favorites",
    title: "Favorites",
    icon: () => <Sidebar.MenuIcon icon="fa fa-star" />,
  },
  {
    key: "archive",
    href: "indexers/archive",
    title: "Archived",
    icon: () => <Sidebar.MenuIcon icon="fa fa-archive" />,
  },
];

function archiveIndexer(indexer, onSuccess) {
  confirmDialog({
    title: `Archive "${indexer.name}"?`,
    description: "Archived indexers no longer appear in the list and stop running for new query results.",
    variant: "danger",
    onConfirm: () =>
      IndexerService.doArchive({ id: indexer.id })
        .then(() => {
          notification.success("Indexer archived.");
          onSuccess();
        })
        .catch(() => notification.error("Failed to archive indexer.")),
  });
}

function buildColumns(currentPage, refresh) {
  return [
    Columns.favorites({ className: "p-r-0" }),
    Columns.custom.sortable(
      (text, indexer) => (
        <React.Fragment>
          <Link className="table-main-title" href={"indexers/" + indexer.id}>
            {indexer.name}
          </Link>
          <IndexerTagsControl
            className="d-block"
            tags={indexer.tags}
            isArchived={indexer.is_archived}
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
    Columns.custom(
      (text, indexer) => {
        const targetTable = get(indexer, "options.target_table") || `indexed_data_${indexer.id}`;
        const dsName = get(indexer, "data_source.name");
        return (
          <span title={`${dsName || ""} → ${targetTable}`}>
            {dsName ? <span className="text-muted">{dsName}.</span> : null}
            {targetTable}
          </span>
        );
      },
      { title: "Target", width: "20%" }
    ),
    Columns.custom(
      (text, indexer) => {
        const strategy = get(indexer, "options.insert_strategy") || "append";
        return (
          <span className={cx("label", strategy === "overwrite" ? "label-warning" : "label-default")}>
            {strategy.toUpperCase()}
          </span>
        );
      },
      { title: "Strategy", width: "1%", className: "text-nowrap" }
    ),
    Columns.timeAgo.sortable({ title: "Last Run", field: "last_triggered_at", width: "1%" }),
    Columns.timeAgo.sortable({ title: "Last Updated At", field: "updated_at", width: "1%" }),
    Columns.dateTime.sortable({ title: "Created At", field: "created_at", width: "1%" }),
    Columns.custom(
      (text, indexer) => {
        const canArchive =
          currentPage !== "archive" &&
          (currentUser.isAdmin || (indexer.user && currentUser.id === indexer.user.id));
        if (!canArchive) {
          return null;
        }
        return (
          <Tooltip title="Archive">
            <PlainButton onClick={() => archiveIndexer(indexer, refresh)}>
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
      return "You don't have any indexers yet.";
    case "favorites":
      return "You haven't marked any indexer as favorite yet.";
    case "archive":
      return "No indexers have been archived.";
    default:
      return null;
  }
}

class IndexersList extends React.Component {
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
      <div className="page-indexers-list">
        <div className="container">
          <ListPageToolbar
            searchPlaceholder="Search Indexers..."
            searchLabel="Search indexers"
            searchValue={controller.searchTerm}
            onSearchChange={controller.updateSearch}
            menu={sidebarMenu}
            selected={currentPage}
            tagsUrl="api/indexers/tags"
            onTagsChange={controller.updateSelectedTags}
            selectedTags={controller.selectedTags}
          />
          <div className="list-page-layout__content">
            {controller.isLoaded && controller.isEmpty ? (
                <DynamicComponent name="IndexersList.EmptyState">
                  {customEmptyText ? (
                    <div className="text-center bg-white tiled p-30">
                      <i className="fa fa-database f-30 text-muted" aria-hidden="true" />
                      <p className="m-t-10 text-muted">{customEmptyText}</p>
                    </div>
                  ) : (
                    <EmptyState
                      icon="fa fa-database"
                      illustration="alert"
                      description="Replicate query results into another data source"
                      helpMessage={<EmptyStateHelpMessage helpTriggerType="ALERTS" />}
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

const IndexersListPage = itemsList(
  IndexersList,
  () =>
    new ResourceItemsSource({
      isPlainList: true,
      getRequest() {
        return {};
      },
      getResource({ params: { currentPage } }) {
        return {
          all: IndexerService.query.bind(IndexerService),
          my: IndexerService.myIndexers.bind(IndexerService),
          favorites: IndexerService.favorites.bind(IndexerService),
          archive: IndexerService.archive.bind(IndexerService),
        }[currentPage];
      },
      getItemProcessor() {
        return item => new Indexer(item);
      },
    }),
  () => new UrlStateStorage({ orderByField: "created_at", orderByReverse: true, itemsPerPage: 20 })
);

routes.register(
  "Indexers.List",
  routeWithUserSession({
    path: "/indexers",
    title: "Indexers",
    render: pageProps => <IndexersListPage {...pageProps} currentPage="all" />,
  })
);
routes.register(
  "Indexers.My",
  routeWithUserSession({
    path: "/indexers/my",
    title: "My Indexers",
    render: pageProps => <IndexersListPage {...pageProps} currentPage="my" />,
  })
);
routes.register(
  "Indexers.Favorites",
  routeWithUserSession({
    path: "/indexers/favorites",
    title: "Favorite Indexers",
    render: pageProps => <IndexersListPage {...pageProps} currentPage="favorites" />,
  })
);
routes.register(
  "Indexers.Archived",
  routeWithUserSession({
    path: "/indexers/archive",
    title: "Archived Indexers",
    render: pageProps => <IndexersListPage {...pageProps} currentPage="archive" />,
  })
);
