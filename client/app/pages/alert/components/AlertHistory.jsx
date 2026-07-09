import React from "react";
import PropTypes from "prop-types";

import Table from "antd/lib/table";
import Button from "antd/lib/button";
import Tag from "antd/lib/tag";
import Tooltip from "@/components/Tooltip";
import notification from "@/services/notification";
import PlainButton from "@/components/PlainButton";
import NotificationContentModal from "@/components/alerts/NotificationContentModal";
import { confirmDialog } from "@/components/ModalShell/confirmDialog";

import AlertEvents from "@/services/alert-events";
import { destinationLabel, statusTag } from "@/pages/alert-events/alertEventUtils";
import TimeAgo from "@/components/TimeAgo";
import { FIXED_TABLE_WIDTHS as W } from "@/components/items-list/fixedTableWidths";
import AlertHistoryChart from "./AlertHistoryChart";
import AlertHistoryTimeline from "./AlertHistoryTimeline";
import AlertSection from "./AlertSection";

import ReloadOutlinedIcon from "@ant-design/icons/ReloadOutlined";
import EyeOutlinedIcon from "@ant-design/icons/EyeOutlined";
import InboxOutlinedIcon from "@ant-design/icons/InboxOutlined";
import DeleteOutlinedIcon from "@ant-design/icons/DeleteOutlined";

import "@/components/items-list/list-page-layout.less";
import "./AlertHistory.less";

const DEFAULT_PAGE_SIZE = 20;

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
    totalCount: 0,
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    selectedEvent: null,
    refreshToken: 0,
  };

  componentDidMount() {
    this.loadPage();
  }

  loadPage = (page = this.state.page, pageSize = this.state.pageSize) => {
    const { alertId } = this.props;
    this.setState({ loading: true, page, pageSize });

    AlertEvents.forAlert({ alertId, page, pageSize })
      .then(({ results, count }) =>
        this.setState({
          events: results,
          totalCount: count,
          loading: false,
        })
      )
      .catch(() => {
        notification.error("Failed to load alert history.");
        this.setState({ loading: false });
      });
  };

  refresh = () => {
    this.setState(state => ({ refreshToken: state.refreshToken + 1 }));
    this.loadPage(this.state.page, this.state.pageSize);
  };

  handlePageChange = (page, pageSize) => {
    this.loadPage(page, pageSize);
  };

  afterEventRemoved = () => {
    const { page, pageSize, totalCount } = this.state;
    const newCount = Math.max(0, totalCount - 1);
    const maxPage = Math.max(1, Math.ceil(newCount / pageSize) || 1);
    this.setState(state => ({ refreshToken: state.refreshToken + 1 }));
    this.loadPage(Math.min(page, maxPage), pageSize);
  };

  archiveEvent = event => {
    AlertEvents.archive({ alertId: event.alert_id, eventId: event.id })
      .then(() => this.afterEventRemoved())
      .catch(() => notification.error("Failed to archive event."));
  };

  deleteEvent = event => {
    confirmDialog({
      title: "Delete this alert event?",
      description: "The event will be permanently removed from history.",
      variant: "danger",
      onConfirm: () =>
        AlertEvents.delete({ alertId: event.alert_id, eventId: event.id })
          .then(() => this.afterEventRemoved())
          .catch(() => notification.error("Failed to delete event.")),
    });
  };

  render() {
    const { canManage } = this.props;
    const { events, loading, totalCount, page, pageSize, selectedEvent, refreshToken } = this.state;

    const columns = [
      {
        title: "Date",
        dataIndex: "created_at",
        render: value => <TimeAgo date={value} variation="timeAgoInTooltip" />,
        width: W.dateTime,
        ellipsis: true,
      },
      {
        title: "State",
        dataIndex: "state",
        render: value => (value ? <Tag>{value.toUpperCase()}</Tag> : null),
        width: 110,
      },
      {
        title: "Status",
        dataIndex: "status",
        render: statusTag,
        width: 100,
      },
      {
        title: "Destination",
        dataIndex: "destination",
        render: (_value, event) => destinationLabel(event),
        ellipsis: true,
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
                <EyeOutlinedIcon aria-hidden="true" />
                <span className="sr-only">view</span>
              </PlainButton>
            </Tooltip>
            {canManage && (
              <Tooltip title="Archive">
                <PlainButton onClick={() => this.archiveEvent(event)} className="m-l-10">
                  <InboxOutlinedIcon aria-hidden="true" />
                  <span className="sr-only">archive</span>
                </PlainButton>
              </Tooltip>
            )}
            {canManage && (
              <Tooltip title="Delete permanently">
                <PlainButton onClick={() => this.deleteEvent(event)} className="m-l-10">
                  <DeleteOutlinedIcon className="text-danger" aria-hidden="true" />
                  <span className="sr-only">delete</span>
                </PlainButton>
              </Tooltip>
            )}
          </span>
        ),
      },
    ];

    return (
      <AlertSection
        className="alert-history"
        title="History"
        action={
          <Button size="small" onClick={this.refresh} loading={loading}>
            <ReloadOutlinedIcon /> Refresh
          </Button>
        }>
        <AlertHistoryTimeline alertId={this.props.alertId} refreshToken={refreshToken} />
        <AlertHistoryChart alertId={this.props.alertId} refreshToken={refreshToken} />
        <div className="list-page-table">
          <Table
            className="table-data"
            rowKey="id"
            size="small"
            loading={loading}
            dataSource={events}
            columns={columns}
            pagination={{
              current: page,
              pageSize,
              total: totalCount,
              hideOnSinglePage: true,
              showSizeChanger: true,
              pageSizeOptions: ["10", "20", "50"],
              onChange: this.handlePageChange,
              onShowSizeChange: this.handlePageChange,
            }}
            locale={{ emptyText: "No notifications have been recorded for this alert yet." }}
          />
        </div>
        <NotificationContentModal
          open={!!selectedEvent}
          event={selectedEvent}
          onClose={() => this.setState({ selectedEvent: null })}
        />
      </AlertSection>
    );
  }
}
