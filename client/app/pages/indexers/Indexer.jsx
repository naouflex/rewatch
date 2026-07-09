import React from "react";
import PropTypes from "prop-types";
import { trim, template, values } from "lodash";

import LoadingState from "@/components/items-list/components/LoadingState";
import CreatePageLayout from "@/components/items-list/CreatePageLayout";
import routeWithUserSession from "@/components/ApplicationArea/routeWithUserSession";
import navigateTo from "@/components/ApplicationArea/navigateTo";

import { currentUser } from "@/services/auth";
import notification from "@/services/notification";
import IndexerService from "@/services/indexer";
import { Query as QueryService } from "@/services/query";
import routes from "@/services/routes";

import MenuButton from "./components/MenuButton";
import IndexerView from "./IndexerView";
import IndexerEdit from "./IndexerEdit";
import IndexerNew from "./IndexerNew";

import "@/components/items-list/create-page-layout.less";
import "./indexers.less";

const MODES = {
  NEW: 0,
  VIEW: 1,
  EDIT: 2,
};

const defaultNameBuilder = template("<%= query.name %> → <%= options.target_table %>");

export function getDefaultName(indexer) {
  if (!indexer || !indexer.query) {
    return "New Indexer";
  }
  const targetTable = (indexer.options && indexer.options.target_table) || `indexed_data_${indexer.id || "<id>"}`;
  return defaultNameBuilder({
    query: indexer.query,
    options: { target_table: targetTable },
  });
}

class Indexer extends React.Component {
  static propTypes = {
    mode: PropTypes.oneOf(values(MODES)),
    indexerId: PropTypes.string,
    onError: PropTypes.func,
  };

  static defaultProps = {
    mode: null,
    indexerId: null,
    onError: () => {},
  };

  _isMounted = false;

  state = {
    indexer: null,
    queryResult: null,
    canEdit: false,
    mode: null,
  };

  componentDidMount() {
    this._isMounted = true;
    const { mode, indexerId } = this.props;
    this.setState({ mode });

    if (mode === MODES.NEW) {
      this.setState({
        indexer: {
          options: { insert_strategy: "append" },
          tags: [],
          data_source: null,
        },
        canEdit: true,
      });
    } else {
      IndexerService.get({ id: indexerId })
        .then(indexer => {
          if (!this._isMounted) return;
          const canEdit = currentUser.canEdit(indexer);
          if (!canEdit) {
            this.setState({ mode: MODES.VIEW });
            notification.warn(
              "You cannot edit this indexer",
              "You do not have sufficient permissions to edit this indexer, and have been redirected to the view-only page.",
              { duration: 0 }
            );
          }
          this.setState({ indexer, canEdit });
          this.onQuerySelected(indexer.query);
        })
        .catch(error => {
          if (this._isMounted) this.props.onError(error);
        });
    }
  }

  componentWillUnmount() {
    this._isMounted = false;
  }

  save = () => {
    const { indexer } = this.state;
    indexer.name = trim(indexer.name) || getDefaultName(indexer);
    const payload = {
      id: indexer.id,
      name: indexer.name,
      options: indexer.options || {},
      tags: indexer.tags || [],
      query_id: indexer.query ? indexer.query.id : null,
      data_source_id: indexer.data_source ? indexer.data_source.id : null,
    };
    return IndexerService.save(payload)
      .then(saved => {
        notification.success("Saved.");
        if (this._isMounted) this.setState({ indexer: { ...indexer, ...saved }, mode: MODES.VIEW });
        navigateTo(`indexers/${saved.id}`, true);
      })
      .catch(() => {
        notification.error("Failed saving indexer.");
      });
  };

  onQuerySelected = query => {
    this.setState(({ indexer }) => ({
      indexer: { ...indexer, query },
      queryResult: null,
    }));

    if (query) {
      new QueryService(query).getQueryResultPromise().then(queryResult => {
        if (this._isMounted) this.setState({ queryResult });
      });
    }
  };

  onNameChange = name => {
    this.setState(({ indexer }) => ({ indexer: { ...indexer, name } }));
  };

  onTagsChange = tags => {
    this.setState(({ indexer }) => ({ indexer: { ...indexer, tags } }));
  };

  onDataSourceChange = dataSourceId => {
    this.setState(({ indexer }) => ({
      indexer: { ...indexer, data_source: dataSourceId ? { id: dataSourceId } : null },
    }));
  };

  setIndexerOptions = obj => {
    this.setState(({ indexer }) => ({
      indexer: { ...indexer, options: { ...(indexer.options || {}), ...obj } },
    }));
  };

  delete = () => {
    const { indexer } = this.state;
    return IndexerService.delete({ id: indexer.id })
      .then(() => {
        notification.success("Indexer deleted successfully.");
        navigateTo("indexers");
      })
      .catch(() => {
        notification.error("Failed deleting indexer.");
      });
  };

  archive = () => {
    const { indexer } = this.state;
    return IndexerService.doArchive({ id: indexer.id })
      .then(updated => {
        notification.success("Indexer archived.");
        if (this._isMounted) this.setState({ indexer: updated });
        navigateTo("indexers/archive");
      })
      .catch(() => notification.error("Failed archiving indexer."));
  };

  unarchive = () => {
    const { indexer } = this.state;
    indexer.is_archived = false;
    return IndexerService.save({
      id: indexer.id,
      name: indexer.name,
      options: indexer.options || {},
      tags: indexer.tags || [],
      is_archived: false,
    })
      .then(saved => {
        notification.success("Indexer unarchived.");
        if (this._isMounted) this.setState({ indexer: saved });
      })
      .catch(() => notification.error("Failed unarchiving indexer."));
  };

  edit = () => {
    const { id } = this.state.indexer;
    navigateTo(`indexers/${id}/edit`, true);
    this.setState({ mode: MODES.EDIT });
  };

  cancel = () => {
    const { id } = this.state.indexer;
    navigateTo(`indexers/${id}`, true);
    this.setState({ mode: MODES.VIEW });
  };

  render() {
    const { indexer } = this.state;
    if (!indexer) return <LoadingState className="m-t-30" />;

    const { queryResult, mode, canEdit } = this.state;
    const menuButton = (
      <MenuButton
        doDelete={this.delete}
        canEdit={canEdit}
        archived={!!indexer.is_archived}
        doArchive={this.archive}
        doUnarchive={this.unarchive}
      />
    );

    const commonProps = {
      indexer,
      queryResult,
      save: this.save,
      menuButton,
      onQuerySelected: this.onQuerySelected,
      onNameChange: this.onNameChange,
      onTagsChange: this.onTagsChange,
      onOptionsChange: this.setIndexerOptions,
      onDataSourceChange: this.onDataSourceChange,
    };

    return (
      <div className="page-create-form">
        <div className="container">
          {mode !== MODES.NEW && <CreatePageLayout backHref="indexers" backLabel="Back to Indexers" />}
          {mode === MODES.NEW && <IndexerNew {...commonProps} />}
          {mode === MODES.VIEW && (
            <IndexerView canEdit={canEdit} onEdit={this.edit} {...commonProps} />
          )}
          {mode === MODES.EDIT && <IndexerEdit cancel={this.cancel} {...commonProps} />}
        </div>
      </div>
    );
  }
}

routes.register(
  "Indexers.New",
  routeWithUserSession({
    path: "/indexers/new",
    title: "New Indexer",
    render: pageProps => <Indexer {...pageProps} mode={MODES.NEW} />,
  })
);
routes.register(
  "Indexers.View",
  routeWithUserSession({
    path: "/indexers/:indexerId",
    title: "Indexer",
    render: pageProps => <Indexer {...pageProps} mode={MODES.VIEW} />,
  })
);
routes.register(
  "Indexers.Edit",
  routeWithUserSession({
    path: "/indexers/:indexerId/edit",
    title: "Indexer",
    render: pageProps => <Indexer {...pageProps} mode={MODES.EDIT} />,
  })
);
