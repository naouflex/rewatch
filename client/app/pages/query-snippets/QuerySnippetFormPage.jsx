import { get, map } from "lodash";
import React from "react";
import PropTypes from "prop-types";

import routeWithUserSession from "@/components/ApplicationArea/routeWithUserSession";
import navigateTo from "@/components/ApplicationArea/navigateTo";
import CreatePageLayout from "@/components/items-list/CreatePageLayout";
import LoadingState from "@/components/items-list/components/LoadingState";
import QuerySnippetForm from "@/components/query-snippets/QuerySnippetForm";

import QuerySnippetService from "@/services/query-snippet";
import { currentUser } from "@/services/auth";
import { policy } from "@/services/policy";
import getTags from "@/services/getTags";
import notification from "@/services/notification";
import routes from "@/services/routes";

function getQuerySnippetTags() {
  return getTags("api/query_snippets/tags").then(tags => map(tags, t => t.name));
}

const canEditQuerySnippet = querySnippet => currentUser.isAdmin || currentUser.id === get(querySnippet, "user.id");

class QuerySnippetFormPage extends React.Component {
  static propTypes = {
    querySnippetId: PropTypes.string,
    onError: PropTypes.func,
  };

  static defaultProps = {
    querySnippetId: "new",
    onError: () => {},
  };

  state = {
    querySnippet: null,
    loading: true,
    saving: false,
  };

  componentDidMount() {
    const { querySnippetId } = this.props;
    const isNew = querySnippetId === "new";

    if (isNew) {
      if (!policy.isCreateQuerySnippetEnabled()) {
        navigateTo("query_snippets", true);
        return;
      }
      this.setState({ querySnippet: {}, loading: false });
      return;
    }

    QuerySnippetService.get({ id: querySnippetId })
      .then(querySnippet => {
        this.setState({ querySnippet, loading: false });
      })
      .catch(error => {
        this.props.onError(error);
        this.setState({ loading: false });
      });
  }

  saveQuerySnippet = values => {
    const { querySnippet } = this.state;
    const payload = querySnippet.id ? { id: querySnippet.id, ...values } : values;
    const saveSnippet = querySnippet.id ? QuerySnippetService.save : QuerySnippetService.create;

    this.setState({ saving: true });
    return saveSnippet(payload)
      .then(() => {
        notification.success(querySnippet.id ? "Query snippet saved." : "Query snippet created.");
        navigateTo("query_snippets", true);
      })
      .finally(() => {
        this.setState({ saving: false });
      });
  };

  render() {
    const { querySnippet, loading, saving } = this.state;
    const isNew = this.props.querySnippetId === "new";
    const readOnly = !isNew && querySnippet && !canEditQuerySnippet(querySnippet);

    if (loading) {
      return (
        <div className="page-create-form">
          <div className="container">
            <LoadingState className="" />
          </div>
        </div>
      );
    }

    if (!querySnippet) {
      return null;
    }

    const pageTitle = isNew ? null : readOnly ? querySnippet.trigger : `Edit ${querySnippet.trigger}`;

    return (
      <div className="page-create-form">
        <div className="container">
          <CreatePageLayout
            backHref="query_snippets"
            backLabel="Back to Query Snippets"
            title={pageTitle}
          />
          <div className="create-page-form__body">
            <p className="create-page-form__intro">
              {readOnly
                ? "View snippet details and SQL template."
                : "Define a trigger keyword and reusable SQL snippet for the query editor."}
            </p>
            <QuerySnippetForm
              querySnippet={querySnippet}
              readOnly={readOnly}
              getAvailableTags={getQuerySnippetTags}
              onSubmit={this.saveQuerySnippet}
              saving={saving}
            />
          </div>
        </div>
      </div>
    );
  }
}

routes.register(
  "QuerySnippets.New",
  routeWithUserSession({
    path: "/query_snippets/new",
    title: "New Query Snippet",
    render: pageProps => <QuerySnippetFormPage {...pageProps} querySnippetId="new" />,
  })
);

routes.register(
  "QuerySnippets.Edit",
  routeWithUserSession({
    path: "/query_snippets/:querySnippetId",
    title: "Query Snippet",
    render: pageProps => <QuerySnippetFormPage {...pageProps} />,
  })
);

export default QuerySnippetFormPage;
