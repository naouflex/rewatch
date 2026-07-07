import React from "react";
import PropTypes from "prop-types";

import Table from "antd/lib/table";
import Button from "antd/lib/button";
import Tooltip from "@/components/Tooltip";
import notification from "@/services/notification";
import PlainButton from "@/components/PlainButton";
import NotificationContentModal from "@/components/alerts/NotificationContentModal";
import { confirmDialog } from "@/components/ModalShell/confirmDialog";

import AlertEvents from "@/services/alert-events";
import { destinationLabel, statusTag } from "@/pages/alert-events/alertEventUtils";
import AlertHistoryWhen from "./AlertHistoryWhen";

import "@/components/items-list/list-page-layout.less";
import "./AlertHistory.less";

export default class AlertHistory extends React.Component {
  static propTypes = {
    alertId: PropTypes.any.isRequired,
    canManage: PropTypes.bool,
  };

  static defaultProps = {
    canManage: false,
  };

  state = {
    events: [],
    loading: true,
    selectedEvent: null,
  };

  componentDidMount() {
    this.refresh();
  }

  refresh = () => {
    const { alertId } = this.props;
    this.setState({ loading: true });
    AlertEvents.forAlert({ alertId, limit: 100 })
      .then(events => this.setState({ events, loading: false }))
      .catch(() => {
        notification.error("Failed to load alert history.");
        this.setState({ loading: false });
      });
  };

  archiveEvent = event => {
    AlertEvents.archive({ alertId: event.alert_id, eventId: event.id })
      .then(() => {
        this.setState(({ events }) => ({
          events: events.filter(e => e.id !== event.id),
        }));
      })
      .catch(() => notification.error("Failed to archive event."));
  };

  deleteEvent = event => {
    confirmDialog({
      title: "Delete this alert event?",
      description: "The event will be permanently removed from history.",
      variant: "danger",
      onConfirm: () =>
        AlertEvents.delete({ alertId: event.alert_id, eventId: event.id })
          .then(() => {
            this.setState(({ events }) => ({
              events: events.filter(e => e.id !== event.id),
            }));
          })
          .catch(() => notification.error("Failed to delete event.")),
    });
  };

  render() {
    const { canManage } = this.props;
    const { events, loading, selectedEvent } = this.state;

    const columns = [
      {
        title: "When",
        dataIndex: "created_at",
        render: value => <AlertHistoryWhen date={value} />,
        width: 140,
        ellipsis: true,
      },
      {
        title: "Status",
        dataIndex: "status",
        render: statusTag,
        width: 100,
      },
      {
        title: "State",
        dataIndex: "state",
        render: value => (value ? <Tag>{value.toUpperCase()}</Tag> : null),
        width: 110,
      },
      {
        title: "Destination",
        dataIndex: "destination",
        render: (_value, event) => destinationLabel(event),
      },
      {
        title: "Row",
        dataIndex: "row_index",
        render: value => (value === null || value === undefined ? "—" : `#${value}`),
        width: 70,
      },
      {
        title: "",
        dataIndex: "id",
        width: 130,
        render: (_id, event) => (
          <span>
            <Tooltip title="Show rendered notification">
              <PlainButton onClick={() => this.setState({ selectedEvent: event })}>
                <i className="fa fa-eye" aria-hidden="true" />
                <span className="sr-only">view</span>
              </PlainButton>
            </Tooltip>
            {canManage && (
              <Tooltip title="Archive">
                <PlainButton onClick={() => this.archiveEvent(event)} className="m-l-10">
                  <i className="fa fa-archive" aria-hidden="true" />
                  <span className="sr-only">archive</span>
                </PlainButton>
              </Tooltip>
            )}
            {canManage && (
              <Tooltip title="Delete permanently">
                <PlainButton onClick={() => this.deleteEvent(event)} className="m-l-10">
                  <i className="fa fa-trash text-danger" aria-hidden="true" />
                  <span className="sr-only">delete</span>
                </PlainButton>
              </Tooltip>
            )}
          </span>
        ),
      },
    ];

    return (
      <div className="alert-history" data-test="AlertHistory">
        <div className="alert-history__header">
          <h4 className="alert-history__title">History</h4>
          <Button size="small" onClick={this.refresh} loading={loading}>
            <i className="fa fa-refresh m-r-5" aria-hidden="true" />
            Refresh
          </Button>
        </div>
        <div className="list-page-table">
          <Table
            rowKey="id"
            size="small"
            loading={loading}
            dataSource={events}
            columns={columns}
            pagination={{ pageSize: 10, hideOnSinglePage: true, showSizeChanger: false }}
            locale={{ emptyText: "No notifications have been recorded for this alert yet." }}
          />
        </div>
        <NotificationContentModal
          open={!!selectedEvent}
          event={selectedEvent}
          onClose={() => this.setState({ selectedEvent: null })}
        />
      </div>
    );
  }
}
