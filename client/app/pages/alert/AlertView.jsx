import React from "react";
import PropTypes from "prop-types";
import cx from "classnames";

import Link from "@/components/Link";
import { Alert as AlertType } from "@/components/proptypes";
import DynamicComponent from "@/components/DynamicComponent";
import Tooltip from "@/components/Tooltip";

import Button from "antd/lib/button";
import Tag from "antd/lib/tag";
import AntAlert from "antd/lib/alert";

import EditOutlinedIcon from "@ant-design/icons/EditOutlined";
import PlayCircleOutlinedIcon from "@ant-design/icons/PlayCircleOutlined";
import PlusOutlinedIcon from "@ant-design/icons/PlusOutlined";
import ExportOutlinedIcon from "@ant-design/icons/ExportOutlined";

import Title from "./components/Title";
import Criteria from "./components/Criteria";
import Rearm from "./components/Rearm";
import Query from "./components/Query";
import AlertDestinations from "./components/AlertDestinations";
import AlertHistory from "./components/AlertHistory";
import AlertSection from "./components/AlertSection";
import AlertStatusStrip from "./components/AlertStatusStrip";
import NotificationTemplateView from "./components/NotificationTemplateView";

export default class AlertView extends React.Component {
  destinationsRef = React.createRef();

  state = {
    unmuting: false,
    evaluating: false,
    subscriptionsRefresh: 0,
  };

  unmute = () => {
    this.setState({ unmuting: true });
    this.props.unmute().finally(() => {
      this.setState({ unmuting: false });
    });
  };

  evaluate = () => {
    this.setState({ evaluating: true });
    this.props.evaluate().finally(() => {
      this.setState({ evaluating: false });
    });
  };

  renderDestinationsAction = () => (
    <Tooltip title='Add an existing alert destination' mouseEnterDelay={0.5}>
      <Button
        data-test="ShowAddAlertSubDialog"
        type="primary"
        size="small"
        onClick={() => this.destinationsRef.current?.showAddAlertSubDialog()}>
        <PlusOutlinedIcon /> Add
      </Button>
    </Tooltip>
  );

  render() {
    const { alert, queryResult, canEdit, onEdit, menuButton } = this.props;
    const { query, name, options, rearm } = alert;
    const queryDataAt = queryResult ? queryResult.getUpdatedAt() : null;

    return (
      <>
        <div className="create-page-form__header">
          <Title name={name} alert={alert}>
            <DynamicComponent name="AlertView.HeaderExtra" alert={alert} />
            {canEdit && (
              <Button type="default" onClick={() => this.evaluate()} loading={this.state.evaluating}>
                <PlayCircleOutlinedIcon /> Evaluate
              </Button>
            )}
            {canEdit ? (
              <Button type="primary" onClick={onEdit}>
                <EditOutlinedIcon /> Edit
              </Button>
            ) : (
              <Tooltip title="You do not have sufficient permissions to edit this alert">
                <Button type="default" className={cx({ disabled: true })}>
                  <EditOutlinedIcon /> Edit
                </Button>
              </Tooltip>
            )}
            {menuButton}
          </Title>
        </div>

        <AlertStatusStrip
          state={alert.state}
          lastTriggered={alert.last_triggered_at}
          queryDataAt={queryDataAt}
          muted={!!options.muted}
        />

        <div className="create-page-form__body">
          <AlertSection title="Query">
            <Query query={query} queryResult={queryResult} />
          </AlertSection>

          {queryResult && options && (
            <>
              <AlertSection title="Rule" className="alert-criteria">
                <Criteria
                  columnNames={queryResult.getColumnNames()}
                  resultValues={queryResult.getData()}
                  alertOptions={options}
                />
              </AlertSection>

              {options.muted && (
                <AntAlert
                  className="m-b-20"
                  message="Notifications are muted"
                  description={
                    canEdit ? (
                      <>
                        Notifications for this alert will not be sent.
                        <Button
                          size="small"
                          type="primary"
                          onClick={this.unmute}
                          loading={this.state.unmuting}
                          className="m-l-5">
                          Unmute
                        </Button>
                      </>
                    ) : (
                      "Notifications for this alert will not be sent."
                    )
                  }
                  type="warning"
                  showIcon
                />
              )}

              <AlertSection
                title="Destinations"
                action={
                  <>
                    <Tooltip title="Open Alert Destinations page in a new tab.">
                      <Link href="destinations" target="_blank" className="alert-destinations-manage-link">
                        Manage <ExportOutlinedIcon aria-hidden="true" />
                      </Link>
                    </Tooltip>
                    {this.renderDestinationsAction()}
                  </>
                }>
                <AlertDestinations
                  ref={this.destinationsRef}
                  alertId={alert.id}
                  hideAddButton
                  onSubscriptionsChange={() =>
                    this.setState(state => ({ subscriptionsRefresh: state.subscriptionsRefresh + 1 }))
                  }
                />
              </AlertSection>

              <AlertSection title="Notifications">
                <Rearm value={rearm || 0} sendForEachRow={!!options.send_for_each_row} />
                <div className="m-t-15">
                    <NotificationTemplateView
                      alert={alert}
                      query={query}
                      columnNames={queryResult.getColumnNames()}
                      resultValues={queryResult.getData()}
                      subject={options.custom_subject}
                      body={options.custom_body}
                      canEdit={canEdit}
                      onEdit={onEdit}
                      subscriptionsRefresh={this.state.subscriptionsRefresh}
                    />
                </div>
              </AlertSection>
            </>
          )}

          {alert.tags && alert.tags.length > 0 && (
            <AlertSection title="Tags">
              {alert.tags.map(t => (
                <Tag key={t} color="blue">
                  {t}
                </Tag>
              ))}
            </AlertSection>
          )}

          <AlertHistory alertId={alert.id} canManage={canEdit} />
        </div>
      </>
    );
  }
}

AlertView.propTypes = {
  alert: AlertType.isRequired,
  queryResult: PropTypes.object, // eslint-disable-line react/forbid-prop-types
  canEdit: PropTypes.bool.isRequired,
  onEdit: PropTypes.func.isRequired,
  menuButton: PropTypes.node.isRequired,
  evaluate: PropTypes.func.isRequired,
  unmute: PropTypes.func,
};

AlertView.defaultProps = {
  queryResult: null,
  unmute: null,
};
