import React from "react";
import { uniqueId } from "lodash";
import Form from "antd/lib/form";
import Input from "antd/lib/input";
import { wrap as wrapDialog, DialogPropType } from "@/components/DialogWrapper";
import { ModalShell } from "@/components/ModalShell";
import { getModalFormProps } from "@/styles/formStyle";

class CreateGroupDialog extends React.Component {
  static propTypes = {
    dialog: DialogPropType.isRequired,
  };

  formId = uniqueId("createGroupForm");

  state = {
    name: "",
  };

  save = () => {
    this.props.dialog.close({
      name: this.state.name,
    });
  };

  render() {
    const { dialog } = this.props;
    return (
      <ModalShell
        dialog={dialog}
        title="Create a New Group"
        description="Organize users and permissions with a named group."
        size="sm"
        okText="Create"
        formId={this.formId}
        onOk={this.save}
        wrapProps={{ "data-test": "CreateGroupDialog" }}>
        <Form id={this.formId} {...getModalFormProps()} onFinish={this.save}>
          <Form.Item label="Group name" required>
            <Input
              value={this.state.name}
              onChange={event => this.setState({ name: event.target.value })}
              onPressEnter={this.save}
              placeholder="e.g. Analysts"
              aria-label="Group name"
              autoFocus
              size="large"
            />
          </Form.Item>
        </Form>
      </ModalShell>
    );
  }
}

export default wrapDialog(CreateGroupDialog);
