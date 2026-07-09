import { get, find } from "lodash";
import React from "react";
import PropTypes from "prop-types";

import routeWithUserSession from "@/components/ApplicationArea/routeWithUserSession";
import { confirmDialog } from "@/components/ModalShell/confirmDialog";
import navigateTo from "@/components/ApplicationArea/navigateTo";
import CreatePageLayout from "@/components/items-list/CreatePageLayout";
import LoadingState from "@/components/items-list/components/LoadingState";
import DynamicForm from "@/components/dynamic-form/DynamicForm";
import helper from "@/components/dynamic-form/dynamicFormHelper";
import ConfigSection from "@/components/ConfigSection/ConfigSection";

import DestinationService, { IMG_ROOT } from "@/services/destination";
import notification from "@/services/notification";
import routes from "@/services/routes";
import DestinationTypePreview from "./DestinationTypePreview";

import "@/components/ConfigSection/ConfigSection.less";
import "@/components/items-list/create-page-layout.less";
import "./DestinationTypePreview.less";

class EditDestination extends React.Component {
  static propTypes = {
    destinationId: PropTypes.string.isRequired,
    onError: PropTypes.func,
  };

  static defaultProps = {
    onError: () => {},
  };

  state = {
    destination: null,
    type: null,
    loading: true,
  };

  componentDidMount() {
    DestinationService.get({ id: this.props.destinationId })
      .then(destination => {
        const { type } = destination;
        this.setState({ destination });
        DestinationService.types().then(types => this.setState({ type: find(types, { type }), loading: false }));
      })
      .catch(error => this.props.onError(error));
  }

  saveDestination = (values, successCallback, errorCallback) => {
    const { destination } = this.state;
    helper.updateTargetWithValues(destination, values);
    DestinationService.save(destination)
      .then(() => successCallback("Saved."))
      .catch(error => {
        const message = get(error, "response.data.message", "Failed saving.");
        errorCallback(message);
      });
  };

  deleteDestination = callback => {
    const { destination } = this.state;

    const doDelete = () => {
      DestinationService.delete(destination)
        .then(() => {
          notification.success("Alert destination deleted successfully.");
          navigateTo("destinations");
        })
        .catch(() => {
          callback();
        });
    };

    confirmDialog({
      title: "Delete Alert Destination",
      description: "Are you sure you want to delete this alert destination?",
      okText: "Delete",
      variant: "danger",
      onConfirm: doDelete,
      onCancel: callback,
    });
  };

  renderForm() {
    const { destination, type } = this.state;
    const fields = helper.getFields(type, destination);
    const formProps = {
      fields,
      type,
      actions: [{ name: "Delete", type: "danger", callback: this.deleteDestination }],
      onSubmit: this.saveDestination,
      defaultShowExtraFields: helper.hasFilledExtraField(type, destination),
      feedbackIcons: true,
    };

    return (
      <div data-test="Destination">
        <div className="destination-edit-header">
          <img src={`${IMG_ROOT}/${type.type}.png`} alt={type.name} />
          <div>
            <h3>{destination.name || type.name}</h3>
            <p>{type.name} destination</p>
          </div>
        </div>

        <DestinationTypePreview type={type} />

        <ConfigSection title="Configuration">
          <DynamicForm {...formProps} />
        </ConfigSection>
      </div>
    );
  }

  render() {
    return (
      <div className="page-create-form">
        <div className="container">
          <CreatePageLayout backHref="destinations" backLabel="Back to Alert Destinations" />
          <div className="create-page-form__body">
            {this.state.loading ? <LoadingState className="" /> : this.renderForm()}
          </div>
        </div>
      </div>
    );
  }
}

routes.register(
  "AlertDestinations.Edit",
  routeWithUserSession({
    path: "/destinations/:destinationId",
    title: "Alert Destinations",
    render: pageProps => <EditDestination {...pageProps} />,
  })
);

export default EditDestination;
