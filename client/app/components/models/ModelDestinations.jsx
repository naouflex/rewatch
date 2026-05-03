import { without, find, includes, map, toLower } from "lodash";
import React from "react";
import PropTypes from "prop-types";

import Link from "@/components/Link";
import Button from "antd/lib/button";
import SelectItemsDialog from "@/components/SelectItemsDialog";
import { Destination as DestinationType, UserProfile as UserType } from "@/components/proptypes";

import DestinationService, { IMG_ROOT } from "@/services/destination";
import MLModelSubscription from "@/services/ml-model-subscription";
import { clientConfig, currentUser } from "@/services/auth";
import notification from "@/services/notification";
import ListItemAddon from "@/components/groups/ListItemAddon";
import EmailSettingsWarning from "@/components/EmailSettingsWarning";
import PlainButton from "@/components/PlainButton";
import Tooltip from "@/components/Tooltip";

import CloseOutlinedIcon from "@ant-design/icons/CloseOutlined";
import Switch from "antd/lib/switch";

import "./ModelDestinations.less";

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
        <EmailSettingsWarning className="destination-warning" featureName="model emails" mode="icon" />
      )}
      {canUnsubscribe && (
        <Tooltip title="Remove" mouseEnterDelay={0.5}>
          <PlainButton className="remove-button" onClick={unsubscribe}>
            {/* TODO: lacks visual feedback */}
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

export default class ModelDestinations extends React.Component {
  static propTypes = {
    modelId: PropTypes.any.isRequired,
  };

  state = {
    dests: [],
    subs: null,
  };

  componentDidMount() {
    const { modelId } = this.props
    Promise.all([
      DestinationService.query(), // get all destinations
      MLModelSubscription.query({ modelId }), // get subcriptions per model
    ]).then(([dests, subs]) => {
      subs = subs.map(normalizeSub);
      this.setState({ dests, subs });
    });
  }

  showAddModelSubDialog = () => {
    const { dests, subs } = this.state;

    SelectItemsDialog.showModal({
      width: 570,
      showCount: true,
      extraFooterContent: (
        <>
          <i className="fa fa-info-circle" aria-hidden="true" /> Create new destinations in{" "}
          <Tooltip title="Opens page in a new tab.">
            <Link href="destinations/new" target="_blank">
            Model Destinations
            </Link>
          </Tooltip>
        </>
      ),
      dialogTitle: "Add Existing Model Destinations",
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
          return Promise.reject(null); // keep dialog visible but suppress its default error message
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
    const { modelId } = this.props;

    const sub = { model_id: modelId };
    if (dest) {
      sub.destination_id = dest.id;
    }

    return MLModelSubscription.create(sub).then(sub => {
      const { subs } = this.state;
      this.setState({
        subs: [...subs, normalizeSub(sub)],
      });
    });
  };

  unsubscribe = sub => {
    MLModelSubscription.delete(sub)
      .then(() => {
        // not showing subscribe notification cause it's redundant here
        const { subs } = this.state;
        this.setState({
          subs: without(subs, sub),
        });
      })
      .catch(() => {
        notification.error("Failed unsubscribing.");
      });
  };

  render() {
    if (!this.props.modelId) {
      return null;
    }

    const { subs } = this.state;
    const currentUserEmailSub = find(subs, {
      destination: { id: USER_EMAIL_DEST_ID },
      user: { id: currentUser.id },
    });
    const filteredSubs = without(subs, currentUserEmailSub);
    const { mailSettingsMissing } = clientConfig;

    return (
      <div className="model-destinations" data-test="ModelDestinations">
        <Tooltip title='Click to add an existing "Model Destination"' mouseEnterDelay={0.5}>
          <Button
            data-test="ShowAddModelSubDialog"
            type="primary"
            size="small"
            className="add-button"
            onClick={this.showAddModelSubDialog}>
            <i className="fa fa-plus f-12 m-r-5" aria-hidden="true" /> Add
          </Button>
        </Tooltip>
        <ul>
          <li className="destination-wrapper">
            <i className="destination-icon fa fa-envelope" aria-hidden="true" />
            <span className="flex-fill">{currentUser.email}</span>
            <EmailSettingsWarning className="destination-warning" featureName="model emails" mode="icon" />
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
