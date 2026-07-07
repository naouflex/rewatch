import { get, map } from "lodash";
import React from "react";

import Modal from "antd/lib/modal";

import routeWithUserSession from "@/components/ApplicationArea/routeWithUserSession";
import navigateTo from "@/components/ApplicationArea/navigateTo";
import Paginator from "@/components/Paginator";
import Tooltip from "@/components/Tooltip";
import PlainButton from "@/components/PlainButton";
import QuerySnippetDialog from "@/components/query-snippets/QuerySnippetDialog";

import { wrap as itemsList, ControllerType } from "@/components/items-list/ItemsList";
import { ResourceItemsSource } from "@/components/items-list/classes/ItemsSource";
import { UrlStateStorage } from "@/components/items-list/classes/StateStorage";

import * as Sidebar from "@/components/items-list/components/Sidebar";
import ListPageToolbar from "@/components/items-list/components/ListPageToolbar";
import ItemsTable, { Columns } from "@/components/items-list/components/ItemsTable";

import QuerySnippetService, { QuerySnippet } from "@/services/query-snippet";
import { currentUser } from "@/services/auth";
import { policy } from "@/services/policy";
import getTags from "@/services/getTags";
import location from "@/services/location";
import notification from "@/services/notification";
import routes from "@/services/routes";

import SnippetContentCell from "./SnippetContentCell";
import "./QuerySnippetsList.less";

function getQuerySnippetTags() {
  return getTags("api/query_snippets/tags").then(tags => map(tags, t => t.name));
}

const sidebarMenu = [
  {
    key: "all",
    href: "query_snippets",
    title: "All Snippets",
    icon: () => <Sidebar.MenuIcon icon="fa fa-scissors" />,
  },
  {
    key: "my",
    href: "query_snippets/my",
    title: "My Snippets",
    icon: () => <Sidebar.ProfileImage user={currentUser} />,
    isAvailable: () => currentUser.hasPermission("list_query_snippets"),
  },
  {
    key: "favorites",
    href: "query_snippets/favorites",
    title: "Favorites",
    icon: () => <Sidebar.MenuIcon icon="fa fa-star" />,
  },
  {
    key: "archive",
    href: "query_snippets/archive",
    title: "Archived",
    icon: () => <Sidebar.MenuIcon icon="fa fa-archive" />,
  },
];

const canEditQuerySnippet = querySnippet => currentUser.isAdmin || currentUser.id === get(querySnippet, "user.id");

function emptyStateContentFor(currentPage) {
  switch (currentPage) {
    case "my":
      return "You don't have any query snippets yet.";
    case "favorites":
      return "You haven't marked any query snippet as favorite yet.";
    case "archive":
      return "No query snippets have been archived.";
    default:
      return "There are no query snippets yet.";
  }
}

class QuerySnippetsList extends React.Component {
  static propTypes = {
    controller: ControllerType.isRequired,
  };

  componentDidMount() {
    const { isNewOrEditPage, querySnippetId } = this.props.controller.params;

    const searchTerm = location.search.q || "";
    if (searchTerm && searchTerm !== this.props.controller.searchTerm) {
      this.props.controller.updateSearch(searchTerm);
    }

    if (isNewOrEditPage) {
      if (querySnippetId === "new") {
        if (policy.isCreateQuerySnippetEnabled()) {
          this.showSnippetDialog();
        } else {
          navigateTo("query_snippets", true);
        }
      } else {
        QuerySnippetService.get({ id: querySnippetId })
          .then(this.showSnippetDialog)
          .catch(error => {
            this.props.controller.handleError(error);
          });
      }
    }
  }

  buildColumns() {
    return [
      Columns.favorites({ className: "p-r-0" }),
      Columns.custom.sortable(
        (text, querySnippet) => (
          <PlainButton type="link" className="table-main-title" onClick={() => this.showSnippetDialog(querySnippet)}>
            {querySnippet.trigger}
          </PlainButton>
        ),
        {
          title: "Trigger",
          field: "trigger",
          className: "text-nowrap",
        }
      ),
      Columns.custom.sortable(text => text, {
        title: "Description",
        field: "description",
        className: "text-nowrap",
      }),
      Columns.custom(snippet => <SnippetContentCell content={snippet} />, {
        title: "Snippet",
        field: "snippet",
      }),
      Columns.avatar({ field: "user", className: "p-l-0 p-r-0" }, name => `Created by ${name}`),
      Columns.dateTime.sortable({
        title: "Created At",
        field: "created_at",
        className: "text-nowrap",
        width: "1%",
      }),
      Columns.custom(
        (text, querySnippet) => {
          if (!canEditQuerySnippet(querySnippet) || querySnippet.is_archived) {
            return null;
          }
          return (
            <Tooltip title="Archive">
              <PlainButton onClick={() => this.archiveQuerySnippet(querySnippet)}>
                <i className="fa fa-archive" aria-hidden="true" />
                <span className="sr-only">archive</span>
              </PlainButton>
            </Tooltip>
          );
        },
        {
          width: "1%",
        }
      ),
      Columns.custom(
        (text, querySnippet) => {
          if (!canEditQuerySnippet(querySnippet)) {
            return null;
          }
          return (
            <Tooltip title="Delete">
              <PlainButton onClick={e => this.deleteQuerySnippet(e, querySnippet)}>
                <i className="fa fa-trash" aria-hidden="true" />
                <span className="sr-only">delete</span>
              </PlainButton>
            </Tooltip>
          );
        },
        {
          width: "1%",
        }
      ),
    ];
  }

  archiveQuerySnippet = querySnippet => {
    Modal.confirm({
      title: `Archive "${querySnippet.trigger}"?`,
      content: "Archived snippets are hidden from the list and autocomplete but can be restored later.",
      okText: "Archive",
      okType: "danger",
      onOk: () =>
        QuerySnippetService.doArchive(querySnippet)
          .then(() => {
            notification.success("Query snippet archived.");
            this.props.controller.update();
          })
          .catch(() => notification.error("Failed to archive query snippet.")),
    });
  };

  saveQuerySnippet = querySnippet => {
    const saveSnippet = querySnippet.id ? QuerySnippetService.save : QuerySnippetService.create;
    return saveSnippet(querySnippet);
  };

  deleteQuerySnippet = (event, querySnippet) => {
    Modal.confirm({
      title: "Delete Query Snippet",
      content: "Are you sure you want to delete this query snippet?",
      okText: "Yes",
      okType: "danger",
      cancelText: "No",
      onOk: () => {
        QuerySnippetService.delete(querySnippet)
          .then(() => {
            notification.success("Query snippet deleted successfully.");
            this.props.controller.update();
          })
          .catch(() => {
            notification.error("Failed deleting query snippet.");
          });
      },
    });
  };

  showSnippetDialog = (querySnippet = null) => {
    const canSave = !querySnippet || canEditQuerySnippet(querySnippet);
    navigateTo("query_snippets/" + get(querySnippet, "id", "new"), true);
    const goToSnippetsList = () => navigateTo("query_snippets", true);
    QuerySnippetDialog.showModal({
      querySnippet,
      readOnly: !canSave,
      getAvailableTags: getQuerySnippetTags,
    })
      .onClose(querySnippet =>
        this.saveQuerySnippet(querySnippet).then(() => {
          this.props.controller.update();
          goToSnippetsList();
        })
      )
      .onDismiss(goToSnippetsList);
  };

  render() {
    const { controller } = this.props;
    const { currentPage } = controller.params;
    const columns = this.buildColumns();

    return (
      <div className="page-query-snippets-list">
        <div className="container">
          <ListPageToolbar
            searchPlaceholder="Search Snippets..."
            searchLabel="Search query snippets"
            searchValue={controller.searchTerm}
            onSearchChange={controller.updateSearch}
            menu={sidebarMenu}
            selected={currentPage}
            tagsUrl="api/query_snippets/tags"
            onTagsChange={controller.updateSelectedTags}
            selectedTags={controller.selectedTags}
          />
          <div className="list-page-layout__content">
            {controller.isLoaded && controller.isEmpty ? (
              <div className="text-center bg-white tiled p-30">
                <i className="fa fa-scissors f-30 text-muted" aria-hidden="true" />
                <p className="m-t-10 text-muted">{emptyStateContentFor(currentPage)}</p>
              </div>
            ) : (
              <div className="list-page-table query-snippets-table">
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

const QuerySnippetsListPage = itemsList(
  QuerySnippetsList,
  () =>
    new ResourceItemsSource({
      isPlainList: true,
      getRequest() {
        return {};
      },
      getResource({ params: { currentPage } }) {
        return {
          all: QuerySnippetService.query.bind(QuerySnippetService),
          my: QuerySnippetService.myQuerySnippets.bind(QuerySnippetService),
          favorites: QuerySnippetService.favorites.bind(QuerySnippetService),
          archive: QuerySnippetService.archive.bind(QuerySnippetService),
        }[currentPage];
      },
      getItemProcessor() {
        return item => new QuerySnippet(item);
      },
    }),
  () => new UrlStateStorage({ orderByField: "trigger", itemsPerPage: 20 })
);

routes.register(
  "QuerySnippets.List",
  routeWithUserSession({
    path: "/query_snippets",
    title: "Query Snippets",
    render: pageProps => <QuerySnippetsListPage {...pageProps} currentPage="all" />,
  })
);
routes.register(
  "QuerySnippets.My",
  routeWithUserSession({
    path: "/query_snippets/my",
    title: "My Query Snippets",
    render: pageProps => <QuerySnippetsListPage {...pageProps} currentPage="my" />,
  })
);
routes.register(
  "QuerySnippets.Favorites",
  routeWithUserSession({
    path: "/query_snippets/favorites",
    title: "Favorite Query Snippets",
    render: pageProps => <QuerySnippetsListPage {...pageProps} currentPage="favorites" />,
  })
);
routes.register(
  "QuerySnippets.Archived",
  routeWithUserSession({
    path: "/query_snippets/archive",
    title: "Archived Query Snippets",
    render: pageProps => <QuerySnippetsListPage {...pageProps} currentPage="archive" />,
  })
);
routes.register(
  "QuerySnippets.NewOrEdit",
  routeWithUserSession({
    path: "/query_snippets/:querySnippetId",
    title: "Query Snippets",
    render: pageProps => <QuerySnippetsListPage {...pageProps} currentPage="all" isNewOrEditPage />,
  })
);
