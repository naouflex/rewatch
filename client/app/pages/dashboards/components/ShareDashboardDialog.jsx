import { replace } from "lodash";
import React from "react";
import { axios } from "@/services/axios";
import PropTypes from "prop-types";
import Switch from "antd/lib/switch";
import Form from "antd/lib/form";
import Alert from "antd/lib/alert";
import notification from "@/services/notification";
import { wrap as wrapDialog, DialogPropType } from "@/components/DialogWrapper";
import { ModalShell, ModalSection } from "@/components/ModalShell";
import InputWithCopy from "@/components/InputWithCopy";
import HelpTrigger from "@/components/HelpTrigger";
import { getModalFormProps } from "@/styles/formStyle";

const API_SHARE_URL = "api/dashboards/{id}/share";

class ShareDashboardDialog extends React.Component {
  static propTypes = {
    dashboard: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
    hasOnlySafeQueries: PropTypes.bool.isRequired,
    dialog: DialogPropType.isRequired,
  };

  constructor(props) {
    super(props);
    const { dashboard } = this.props;

    this.state = {
      saving: false,
    };

    this.apiUrl = replace(API_SHARE_URL, "{id}", dashboard.id);
    this.enabled = this.props.hasOnlySafeQueries || dashboard.publicAccessEnabled;
  }

  enableAccess = () => {
    const { dashboard } = this.props;
    this.setState({ saving: true });

    axios
      .post(this.apiUrl)
      .then(data => {
        dashboard.publicAccessEnabled = true;
        dashboard.public_url = data.public_url;
      })
      .catch(() => {
        notification.error("Failed to turn on sharing for this dashboard");
      })
      .finally(() => {
        this.setState({ saving: false });
      });
  };

  disableAccess = () => {
    const { dashboard } = this.props;
    this.setState({ saving: true });

    axios
      .delete(this.apiUrl)
      .then(() => {
        dashboard.publicAccessEnabled = false;
        delete dashboard.public_url;
      })
      .catch(() => {
        notification.error("Failed to turn off sharing for this dashboard");
      })
      .finally(() => {
        this.setState({ saving: false });
      });
  };

  onChange = checked => {
    if (checked) {
      this.enableAccess();
    } else {
      this.disableAccess();
    }
  };

  render() {
    const { dialog, dashboard, hasOnlySafeQueries } = this.props;
    return (
      <ModalShell
        dialog={dialog}
        title="Share Dashboard"
        description={
          <>
            Allow public access to this dashboard with a secret address. <HelpTrigger type="SHARE_DASHBOARD" />
          </>
        }
        size="md"
        footer={null}>
        <Form {...getModalFormProps()}>
          {!hasOnlySafeQueries && (
            <ModalSection>
              <Alert
                message="For your security, sharing is currently not supported for dashboards containing queries with text parameters. Consider changing the text parameters in your query to a different type."
                type="error"
              />
            </ModalSection>
          )}
          <ModalSection title="Public access">
            <Form.Item label="Allow public access">
              <Switch
                checked={dashboard.publicAccessEnabled}
                onChange={this.onChange}
                loading={this.state.saving}
                disabled={!this.enabled}
                data-test="PublicAccessEnabled"
              />
            </Form.Item>
            {dashboard.public_url && (
              <Form.Item label="Secret address">
                <InputWithCopy value={dashboard.public_url} data-test="SecretAddress" />
              </Form.Item>
            )}
          </ModalSection>
        </Form>
      </ModalShell>
    );
  }
}

export default wrapDialog(ShareDashboardDialog);
