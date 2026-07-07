import React from "react";
import PropTypes from "prop-types";
import { isEmpty, get } from "lodash";

import Table from "antd/lib/table";
import Tag from "antd/lib/tag";
import Button from "antd/lib/button";
import Modal from "antd/lib/modal";
import Tooltip from "@/components/Tooltip";
import notification from "@/services/notification";
import TimeAgo from "@/components/TimeAgo";
import PlainButton from "@/components/PlainButton";

import AlertEvents from "@/services/alert-events";
import AlertHistoryWhen from "./AlertHistoryWhen";

import "@/components/items-list/list-page-layout.less";
import "./AlertHistory.less";

const STATUS_COLORS = {
  ok: "green",
  error: "red",
};

function statusTag(status) {
  if (!status) {
    return null;
  }
  return <Tag color={STATUS_COLORS[status] || "blue"}>{status.toUpperCase()}</Tag>;
}

function destinationLabel(event) {
  if (event.destination) {
    return `${event.destination.name} (${event.destination.type})`;
  }
  if (event.alert_type) {
    return event.alert_type;
  }
  return "—";
}

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
    Modal.confirm({
      title: "Delete this alert event?",
      content: "The event will be permanently removed from history.",
      okType: "danger",
      onOk: () =>
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
        <Modal
          title="Notification content"
          open={!!selectedEvent}
          onCancel={() => this.setState({ selectedEvent: null })}
          footer={null}
          width={720}>
          {selectedEvent && (
            <div>
              <p className="text-muted">
                <TimeAgo date={selectedEvent.created_at} /> · {destinationLabel(selectedEvent)} ·{" "}
                {statusTag(selectedEvent.status)}
              </p>
              {!isEmpty(get(selectedEvent, "additional_properties.error")) && (
                <pre className="text-danger">{selectedEvent.additional_properties.error}</pre>
              )}
              <pre style={{ whiteSpace: "pre-wrap", maxHeight: 400, overflow: "auto" }}>
                {selectedEvent.content || "(no content recorded)"}
              </pre>
            </div>
          )}
        </Modal>
      </div>
    );
  }
}
