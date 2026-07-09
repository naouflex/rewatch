import { without, find, includes, map, toLower } from "lodash";
import React from "react";
import PropTypes from "prop-types";

import Link from "@/components/Link";
import Button from "antd/lib/button";
import SelectItemsDialog from "@/components/SelectItemsDialog";
import { Destination as DestinationType, UserProfile as UserType } from "@/components/proptypes";

import DestinationService, { IMG_ROOT } from "@/services/destination";
import AlertSubscription from "@/services/alert-subscription";
import { clientConfig, currentUser } from "@/services/auth";
import notification from "@/services/notification";
import ListItemAddon from "@/components/groups/ListItemAddon";
import EmailSettingsWarning from "@/components/EmailSettingsWarning";
import PlainButton from "@/components/PlainButton";
import Tooltip from "@/components/Tooltip";

import CloseOutlinedIcon from "@ant-design/icons/CloseOutlined";
import PlusOutlinedIcon from "@ant-design/icons/PlusOutlined";
import MailOutlinedIcon from "@ant-design/icons/MailOutlined";
import Switch from "antd/lib/switch";

import "./AlertDestinations.less";

const USER_EMAIL_DEST_ID = -1;

function normalizeSub(sub) {
  if (!sub.destination) {
    sub.destination = {
      id: USER_EMAIL_DEST_ID,
      name: sub.user.email,
      icon: "DEPRECATED",
      type: "email",
    };
  }
  return sub;
}

function ListItem({ destination: { name, type }, user, unsubscribe }) {
  const canUnsubscribe = currentUser.isAdmin || currentUser.id === user.id;

  return (
    <li className="destination-wrapper">
      <img src={`${IMG_ROOT}/${type}.png`} className="destination-icon" alt={name} />
      <span className="flex-fill">{name}</span>
      {type === "email" && (
        <EmailSettingsWarning className="destination-warning" featureName="alert emails" mode="icon" />
      )}
      {canUnsubscribe && (
        <Tooltip title="Remove" mouseEnterDelay={0.5}>
          <PlainButton className="remove-button" onClick={unsubscribe}>
            <CloseOutlinedIcon />
          </PlainButton>
        </Tooltip>
      )}
    </li>
  );
}

ListItem.propTypes = {
  destination: DestinationType.isRequired,
  user: UserType.isRequired,
  unsubscribe: PropTypes.func.isRequired,
};

export default class AlertDestinations extends React.Component {
  static propTypes = {
    alertId: PropTypes.any,
    hideAddButton: PropTypes.bool,
    onSubscriptionsChange: PropTypes.func,
  };

  static defaultProps = {
    alertId: null,
    hideAddButton: false,
    onSubscriptionsChange: null,
  };

  state = {
    dests: [],
    subs: null,
  };

  componentDidMount() {
    if (this.props.alertId) {
      this.loadSubscriptions();
    }
  }

  componentDidUpdate(prevProps) {
    if (this.props.alertId && this.props.alertId !== prevProps.alertId) {
      this.loadSubscriptions();
    }
  }

  loadSubscriptions = () => {
    const { alertId } = this.props;
    Promise.all([DestinationService.query(), AlertSubscription.query({ alertId })]).then(([dests, subs]) => {
      subs = subs.map(normalizeSub);
      this.setState({ dests, subs });
      this.props.onSubscriptionsChange?.(subs);
    });
  };

  showAddAlertSubDialog = () => {
    const { dests, subs } = this.state;

    SelectItemsDialog.showModal({
      width: 570,
      showCount: true,
      extraFooterContent: (
        <>
          Create new destinations in{" "}
          <Tooltip title="Opens page in a new tab.">
            <Link href="destinations/new" target="_blank">
              Alert Destinations
            </Link>
          </Tooltip>
        </>
      ),
      dialogTitle: "Add Existing Alert Destinations",
      inputPlaceholder: "Search destinations...",
      searchItems: searchTerm => {
        searchTerm = toLower(searchTerm);
        return Promise.resolve(dests.filter(d => includes(toLower(d.name), searchTerm)));
      },
      renderItem: (item, { isSelected }) => {
        const alreadyInGroup = !!find(subs, s => s.destination.id === item.id);

        return {
          content: (
            <div className="destination-wrapper">
              <img src={`${IMG_ROOT}/${item.type}.png`} className="destination-icon" alt={item.name} />
              <span className="flex-fill">{item.name}</span>
              <ListItemAddon isSelected={isSelected} alreadyInGroup={alreadyInGroup} deselectedIcon="fa-plus" />
            </div>
          ),
          isDisabled: alreadyInGroup,
          className: isSelected || alreadyInGroup ? "selected" : "",
        };
      },
    }).onClose(items => {
      const promises = map(items, item => this.subscribe(item));
      return Promise.all(promises)
        .then(() => {
          notification.success("Subscribed.");
        })
        .catch(() => {
          notification.error("Failed saving subscription.");
          return Promise.reject(null);
        });
    });
  };

  onUserEmailToggle = sub => {
    if (sub) {
      this.unsubscribe(sub);
    } else {
      this.subscribe();
    }
  };

  subscribe = dest => {
    const { alertId } = this.props;

    const sub = { alert_id: alertId };
    if (dest) {
      sub.destination_id = dest.id;
    }

    return AlertSubscription.create(sub).then(sub => {
      const { subs } = this.state;
      const nextSubs = [...subs, normalizeSub(sub)];
      this.setState({
        subs: nextSubs,
      });
      this.props.onSubscriptionsChange?.(nextSubs);
    });
  };

  unsubscribe = sub => {
    AlertSubscription.delete(sub)
      .then(() => {
        const { subs } = this.state;
        const nextSubs = without(subs, sub);
        this.setState({
          subs: nextSubs,
        });
        this.props.onSubscriptionsChange?.(nextSubs);
      })
      .catch(() => {
        notification.error("Failed unsubscribing.");
      });
  };

  renderAddButton() {
    return (
      <Tooltip title='Add an existing alert destination' mouseEnterDelay={0.5}>
        <Button
          data-test="ShowAddAlertSubDialog"
          type="primary"
          size="small"
          onClick={this.showAddAlertSubDialog}>
          <PlusOutlinedIcon /> Add
        </Button>
      </Tooltip>
    );
  }

  render() {
    const { alertId, hideAddButton } = this.props;

    if (!alertId) {
      return (
        <div className="alert-destinations alert-destinations--placeholder">
          Save the alert first to configure notification destinations.
        </div>
      );
    }

    const { subs } = this.state;
    const currentUserEmailSub = find(subs, {
      destination: { id: USER_EMAIL_DEST_ID },
      user: { id: currentUser.id },
    });
    const filteredSubs = without(subs, currentUserEmailSub);
    const { mailSettingsMissing } = clientConfig;

    return (
      <div className="alert-destinations" data-test="AlertDestinations">
        {!hideAddButton && this.renderAddButton()}
        <ul>
          <li className="destination-wrapper">
            <MailOutlinedIcon className="destination-icon destination-icon--ant" aria-hidden="true" />
            <span className="flex-fill">{currentUser.email}</span>
            <EmailSettingsWarning className="destination-warning" featureName="alert emails" mode="icon" />
            {!mailSettingsMissing && (
              <Switch
                size="small"
                className="toggle-button"
                checked={!!currentUserEmailSub}
                loading={!subs}
                onChange={() => this.onUserEmailToggle(currentUserEmailSub)}
                data-test="UserEmailToggle"
              />
            )}
          </li>
          {filteredSubs.map(s => (
            <ListItem key={s.id} unsubscribe={() => this.unsubscribe(s)} {...s} />
          ))}
        </ul>
      </div>
    );
  }
}
