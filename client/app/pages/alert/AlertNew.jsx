import React from "react";
import PropTypes from "prop-types";

import HelpTrigger from "@/components/HelpTrigger";
import CreatePageLayout from "@/components/items-list/CreatePageLayout";
import { Alert as AlertType } from "@/components/proptypes";

import Button from "antd/lib/button";

import LoadingOutlinedIcon from "@ant-design/icons/LoadingOutlined";
import QuestionCircleOutlinedIcon from "@ant-design/icons/QuestionCircleOutlined";

import Title from "./components/Title";
import Criteria from "./components/Criteria";
import NotificationTemplate from "./components/NotificationTemplate";
import Rearm from "./components/Rearm";
import Query from "./components/Query";
import AlertDestinations from "./components/AlertDestinations";
import AlertSection from "./components/AlertSection";

export default class AlertNew extends React.Component {
  state = {
    saving: false,
  };

  save = () => {
    this.setState({ saving: true });
    this.props.save().catch(() => {
      this.setState({ saving: false });
    });
  };

  render() {
    const { alert, queryResult, pendingRearm, onNotificationTemplateChange } = this.props;
    const { onQuerySelected, onNameChange, onRearmChange, onCriteriaChange } = this.props;
    const { query, name, options } = alert;
    const { saving } = this.state;

    return (
      <>
        <CreatePageLayout backHref="alerts" backLabel="Back to Alerts" />
        <div className="create-page-form__header">
          <Title alert={alert} name={name} onChange={onNameChange} editMode />
        </div>
        <div className="create-page-form__body">
          <p className="create-page-form__intro">
            Select the query you want to monitor. Alerts do not work with queries that use parameters.
          </p>

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

              <AlertSection title="Destinations">
                <AlertDestinations />
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

          <div className="create-page-form__footer">
            <Button type="primary" onClick={this.save} disabled={!query} loading={saving}>
              {saving && <LoadingOutlinedIcon />}
              Create Alert
            </Button>
          </div>

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

AlertNew.propTypes = {
  alert: AlertType.isRequired,
  queryResult: PropTypes.object, // eslint-disable-line react/forbid-prop-types
  pendingRearm: PropTypes.number,
  onQuerySelected: PropTypes.func.isRequired,
  save: PropTypes.func.isRequired,
  onNameChange: PropTypes.func.isRequired,
  onRearmChange: PropTypes.func.isRequired,
  onCriteriaChange: PropTypes.func.isRequired,
  onNotificationTemplateChange: PropTypes.func.isRequired,
};

AlertNew.defaultProps = {
  queryResult: null,
  pendingRearm: null,
};
