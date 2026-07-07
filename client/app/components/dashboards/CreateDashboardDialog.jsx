import { trim } from "lodash";
import React, { useState } from "react";
import Form from "antd/lib/form";
import Input from "antd/lib/input";
import DynamicComponent from "@/components/DynamicComponent";
import { wrap as wrapDialog, DialogPropType } from "@/components/DialogWrapper";
import { ModalShell } from "@/components/ModalShell";
import { useUniqueId } from "@/lib/hooks/useUniqueId";
import navigateTo from "@/components/ApplicationArea/navigateTo";
import recordEvent from "@/services/recordEvent";
import { policy } from "@/services/policy";
import { Dashboard } from "@/services/dashboard";
import { getModalFormProps } from "@/styles/formStyle";

function CreateDashboardDialog({ dialog }) {
  const [name, setName] = useState("");
  const [isValid, setIsValid] = useState(false);
  const [saveInProgress, setSaveInProgress] = useState(false);
  const isCreateDashboardEnabled = policy.isCreateDashboardEnabled();
  const formId = useUniqueId("createDashboardForm");

  function handleNameChange(event) {
    const value = trim(event.target.value);
    setName(value);
    setIsValid(value !== "");
  }

  function save() {
    if (name !== "") {
      setSaveInProgress(true);

      Dashboard.save({ name }).then(data => {
        dialog.close();
        navigateTo(`${data.url}?edit`);
      });
      recordEvent("create", "dashboard");
    }
  }

  return (
    <ModalShell
      dialog={dialog}
      title="New Dashboard"
      description="Give your dashboard a name to get started."
      size="sm"
      okText="Create"
      cancelText="Close"
      formId={formId}
      onOk={save}
      showSubmit={isCreateDashboardEnabled}
      footer={isCreateDashboardEnabled ? "submit-cancel" : "close"}
      okButtonProps={{
        disabled: !isValid || saveInProgress,
        loading: saveInProgress,
        "data-test": "DashboardSaveButton",
      }}
      cancelButtonProps={{
        disabled: saveInProgress,
      }}
      closable={!saveInProgress}
      maskClosable={!saveInProgress}
      wrapProps={{
        "data-test": "CreateDashboardDialog",
      }}>
      <DynamicComponent name="CreateDashboardDialogExtra" disabled={!isCreateDashboardEnabled}>
        <Form id={formId} {...getModalFormProps()} onFinish={save}>
          <Form.Item label="Dashboard name" required>
            <Input
              value={name}
              onChange={handleNameChange}
              onPressEnter={save}
              placeholder="e.g. Product metrics"
              aria-label="Dashboard name"
              disabled={saveInProgress || !isCreateDashboardEnabled}
              autoFocus
              size="large"
            />
          </Form.Item>
        </Form>
      </DynamicComponent>
    </ModalShell>
  );
}

CreateDashboardDialog.propTypes = {
  dialog: DialogPropType.isRequired,
};

export default wrapDialog(CreateDashboardDialog);
