import { isEmpty, includes, get, reject } from "lodash";
import React from "react";

import Button from "antd/lib/button";
import List from "antd/lib/list";
import Input from "antd/lib/input";
import Steps from "antd/lib/steps";

import routeWithUserSession from "@/components/ApplicationArea/routeWithUserSession";
import navigateTo from "@/components/ApplicationArea/navigateTo";
import CreatePageLayout from "@/components/items-list/CreatePageLayout";
import LoadingState from "@/components/items-list/components/LoadingState";
import { PreviewCard } from "@/components/PreviewCard";
import EmptyState from "@/components/items-list/components/EmptyState";
import DynamicForm from "@/components/dynamic-form/DynamicForm";
import helper from "@/components/dynamic-form/dynamicFormHelper";
import ConfigSection from "@/components/ConfigSection/ConfigSection";
import DestinationTypePreview from "./DestinationTypePreview";

import DestinationService, { IMG_ROOT } from "@/services/destination";
import { policy } from "@/services/policy";
import notification from "@/services/notification";
import routes from "@/services/routes";

import "@/components/ConfigSection/ConfigSection.less";
import "./DestinationTypePreview.less";

const { Search } = Input;
const { Step } = Steps;

const StepEnum = {
  SELECT_TYPE: 0,
  CONFIGURE_IT: 1,
};

class NewDestination extends React.Component {
  state = {
    loading: true,
    types: [],
    searchText: "",
    selectedType: null,
    currentStep: StepEnum.SELECT_TYPE,
    saving: false,
  };

  componentDidMount() {
    if (!policy.canCreateDestination()) {
      navigateTo("destinations", true);
      return;
    }
    DestinationService.types()
      .then(types => this.setState({ types: reject(types, "deprecated"), loading: false }))
      .catch(() => this.setState({ loading: false }));
  }

  selectType = selectedType => {
    this.setState({ selectedType, currentStep: StepEnum.CONFIGURE_IT });
  };

  resetType = () => {
    this.setState({ selectedType: null, searchText: "", currentStep: StepEnum.SELECT_TYPE });
  };

  createDestination = (values, successCallback, errorCallback) => {
    if (this.state.saving) {
      return;
    }
    const { selectedType } = this.state;
    this.setState({ saving: true });

    const target = { options: {}, type: selectedType.type };
    helper.updateTargetWithValues(target, values);

    DestinationService.create(target)
      .then(destination => {
        successCallback("Saved.");
        notification.success("Alert destination created successfully.");
        navigateTo(`destinations/${destination.id}`);
      })
      .catch(error => {
        this.setState({ saving: false });
        errorCallback(get(error, "response.data.message", "Failed saving."));
      });
  };

  renderTypeSelector() {
    const { types, searchText } = this.state;
    const filteredTypes = types.filter(
      type => isEmpty(searchText) || includes(type.name.toLowerCase(), searchText.toLowerCase())
    );

    return (
      <div className="m-t-10">
        <Search
          placeholder="Search..."
          aria-label="Search"
          onChange={e => this.setState({ searchText: e.target.value })}
          autoFocus
        />
        <div className="scrollbox p-5 m-t-10" style={{ minHeight: "30vh", maxHeight: "50vh" }}>
          {isEmpty(filteredTypes) ? (
            <EmptyState className="" />
          ) : (
            <List
              size="small"
              dataSource={filteredTypes}
              renderItem={item => (
                <List.Item className="p-l-10 p-r-10 clickable" onClick={() => this.selectType(item)}>
                  <PreviewCard title={item.name} imageUrl={`${IMG_ROOT}/${item.type}.png`} roundedImage={false}>
                    <i className="fa fa-angle-double-right" aria-hidden="true" />
                  </PreviewCard>
                </List.Item>
              )}
            />
          )}
        </div>
      </div>
    );
  }

  renderForm() {
    const { selectedType } = this.state;
    const fields = helper.getFields(selectedType);

    return (
      <div>
        <div className="d-flex justify-content-center align-items-center m-b-10">
          <img className="p-5" src={`${IMG_ROOT}/${selectedType.type}.png`} alt={selectedType.name} width="48" />
          <h4 className="m-0">{selectedType.name}</h4>
        </div>
        <DestinationTypePreview type={selectedType} />
        <ConfigSection title="Configuration" className="m-t-15">
          <DynamicForm fields={fields} onSubmit={this.createDestination} feedbackIcons saveText="Create" />
        </ConfigSection>
      </div>
    );
  }

  render() {
    const { loading, currentStep } = this.state;

    return (
      <div className="page-create-form">
        <div className="container">
          <CreatePageLayout backHref="destinations" backLabel="Back to Alert Destinations" />
          <div className="create-page-form__body">
            <Steps className="hidden-xs m-b-20" size="small" current={currentStep} progressDot>
              <Step title="Type Selection" />
              <Step title="Configuration" />
            </Steps>
            {loading && <LoadingState className="" />}
            {!loading && currentStep === StepEnum.SELECT_TYPE && this.renderTypeSelector()}
            {!loading && currentStep === StepEnum.CONFIGURE_IT && (
              <React.Fragment>
                <div className="m-b-10">
                  <Button onClick={this.resetType}>
                    <i className="fa fa-angle-left m-r-5" aria-hidden="true" />
                    Change type
                  </Button>
                </div>
                {this.renderForm()}
              </React.Fragment>
            )}
          </div>
        </div>
      </div>
    );
  }
}

routes.register(
  "AlertDestinations.New",
  routeWithUserSession({
    path: "/destinations/new",
    title: "New Alert Destination",
    render: pageProps => <NewDestination {...pageProps} />,
  })
);
