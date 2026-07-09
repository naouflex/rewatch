import React from "react";
import PropTypes from "prop-types";

import HelpTrigger from "@/components/HelpTrigger";
import DynamicComponent from "@/components/DynamicComponent";
import Link from "@/components/Link";
import Tooltip from "@/components/Tooltip";
import { Alert as AlertType } from "@/components/proptypes";

import Button from "antd/lib/button";
import Select from "antd/lib/select";

import CloseOutlinedIcon from "@ant-design/icons/CloseOutlined";
import CheckOutlinedIcon from "@ant-design/icons/CheckOutlined";
import LoadingOutlinedIcon from "@ant-design/icons/LoadingOutlined";
import PlayCircleOutlinedIcon from "@ant-design/icons/PlayCircleOutlined";
import PlusOutlinedIcon from "@ant-design/icons/PlusOutlined";
import ExportOutlinedIcon from "@ant-design/icons/ExportOutlined";
import QuestionCircleOutlinedIcon from "@ant-design/icons/QuestionCircleOutlined";

import Title from "./components/Title";
import Criteria from "./components/Criteria";
import NotificationTemplate from "./components/NotificationTemplate";
import Rearm from "./components/Rearm";
import Query from "./components/Query";
import AlertDestinations from "./components/AlertDestinations";
import AlertSection from "./components/AlertSection";
import AlertStatusStrip from "./components/AlertStatusStrip";

export default class AlertEdit extends React.Component {
  destinationsRef = React.createRef();

  _isMounted = false;

  state = {
    saving: false,
    evaluating: false,
    subscriptionsRefresh: 0,
  };

  componentDidMount() {
    this._isMounted = true;
  }

  componentWillUnmount() {
    this._isMounted = false;
  }

  save = () => {
    this.setState({ saving: true });
    this.props.save().catch(() => {
      if (this._isMounted) {
        this.setState({ saving: false });
      }
    });
  };

  evaluate = () => {
    this.setState({ evaluating: true });
    this.props.evaluate().finally(() => {
      if (this._isMounted) {
        this.setState({ evaluating: false });
      }
    });
  };

  render() {
    const { alert, queryResult, pendingRearm, onNotificationTemplateChange, menuButton, onTagsChange, evaluate } =
      this.props;
    const { onQuerySelected, onNameChange, onRearmChange, onCriteriaChange } = this.props;
    const { query, name, options, tags } = alert;
    const { saving, evaluating } = this.state;
    const queryDataAt = queryResult ? queryResult.getUpdatedAt() : null;

    return (
      <>
        <div className="create-page-form__header">
          <Title name={name} alert={alert} onChange={onNameChange} editMode>
            <DynamicComponent name="AlertEdit.HeaderExtra" alert={alert} />
            {evaluate && (
              <Button onClick={() => this.evaluate()} loading={evaluating}>
                <PlayCircleOutlinedIcon /> Evaluate
              </Button>
            )}
            <Button onClick={() => this.props.cancel()}>
              <CloseOutlinedIcon /> Cancel
            </Button>
            <Button type="primary" onClick={() => this.save()} loading={saving}>
              {saving ? (
                <>
                  <LoadingOutlinedIcon />
                  <span className="sr-only">Saving...</span>
                </>
              ) : (
                <CheckOutlinedIcon />
              )}
              Save Changes
            </Button>
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
            <Query query={query} queryResult={queryResult} onChange={onQuerySelected} editMode />
          </AlertSection>

          {queryResult && options && (
            <>
              <AlertSection title="Rule" className="alert-criteria">
                <Criteria
                  columnNames={queryResult.getColumnNames()}
                  resultValues={queryResult.getData()}
                  alertOptions={options}
                  onChange={onCriteriaChange}
                  editMode
                />
              </AlertSection>

              <AlertSection
                title="Destinations"
                action={
                  <>
                    <Tooltip title="Open Alert Destinations page in a new tab.">
                      <Link href="destinations" target="_blank" className="alert-destinations-manage-link">
                        Manage <ExportOutlinedIcon aria-hidden="true" />
                      </Link>
                    </Tooltip>
                    <Tooltip title='Add an existing alert destination' mouseEnterDelay={0.5}>
                      <Button
                        data-test="ShowAddAlertSubDialog"
                        type="primary"
                        size="small"
                        onClick={() => this.destinationsRef.current?.showAddAlertSubDialog()}>
                        <PlusOutlinedIcon /> Add
                      </Button>
                    </Tooltip>
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

              <AlertSection
                title="Notifications"
                help={
                  options.send_for_each_row
                    ? "When sending one notification per row, the current row is exposed to the template via QUERY_RESULT_ROW (and overrides QUERY_RESULT_VALUE)."
                    : null
                }>
                <Rearm
                  value={pendingRearm || 0}
                  onChange={onRearmChange}
                  sendForEachRow={!!options.send_for_each_row}
                  onSendForEachRowChange={checked => onCriteriaChange({ send_for_each_row: checked })}
                  editMode
                />
              </AlertSection>

              <AlertSection title="Template">
                <NotificationTemplate
                  alert={alert}
                  query={query}
                  alertId={alert.id}
                  subscriptionsRefresh={this.state.subscriptionsRefresh}
                  columnNames={queryResult.getColumnNames()}
                  resultValues={queryResult.getData()}
                  subject={options.custom_subject}
                  setSubject={subject => onNotificationTemplateChange({ custom_subject: subject })}
                  body={options.custom_body}
                  setBody={body => onNotificationTemplateChange({ custom_body: body })}
                />
              </AlertSection>
            </>
          )}

          <AlertSection title="Tags" help="Press enter to add a tag.">
            <Select
              mode="tags"
              style={{ width: "100%", maxWidth: 400 }}
              value={tags || []}
              onChange={onTagsChange}
              tokenSeparators={[","]}
              placeholder="Add tags"
            />
          </AlertSection>

          <div className="alert-edit-help">
            <HelpTrigger className="f-13" type="ALERT_SETUP">
              <QuestionCircleOutlinedIcon aria-hidden="true" /> Setup Instructions
            </HelpTrigger>
          </div>
        </div>
      </>
    );
  }
}

AlertEdit.propTypes = {
  alert: AlertType.isRequired,
  queryResult: PropTypes.object, // eslint-disable-line react/forbid-prop-types
  pendingRearm: PropTypes.number,
  menuButton: PropTypes.node.isRequired,
  save: PropTypes.func.isRequired,
  cancel: PropTypes.func.isRequired,
  evaluate: PropTypes.func,
  onQuerySelected: PropTypes.func.isRequired,
  onNameChange: PropTypes.func.isRequired,
  onCriteriaChange: PropTypes.func.isRequired,
  onRearmChange: PropTypes.func.isRequired,
  onNotificationTemplateChange: PropTypes.func.isRequired,
  onTagsChange: PropTypes.func.isRequired,
};

AlertEdit.defaultProps = {
  queryResult: null,
  pendingRearm: null,
  evaluate: null,
};
