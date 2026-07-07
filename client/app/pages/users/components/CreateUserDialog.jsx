import React, { useState, useEffect, useCallback } from "react";
import Alert from "antd/lib/alert";
import DynamicForm from "@/components/dynamic-form/DynamicForm";
import { wrap as wrapDialog, DialogPropType } from "@/components/DialogWrapper";
import { ModalShell, ModalSection } from "@/components/ModalShell";
import recordEvent from "@/services/recordEvent";
import { useUniqueId } from "@/lib/hooks/useUniqueId";

const formFields = [
  { required: true, name: "name", title: "Name", type: "text", autoFocus: true },
  { required: true, name: "email", title: "Email", type: "email" },
];

function CreateUserDialog({ dialog }) {
  const [error, setError] = useState(null);
  useEffect(() => {
    recordEvent("view", "page", "users/new");
  }, []);

  const handleSubmit = useCallback(values => dialog.close(values).catch(setError), [dialog]);
  const formId = useUniqueId("userForm");

  return (
    <ModalShell
      dialog={dialog}
      title="Create a New User"
      description="Invite a team member with their name and email address."
      size="md"
      okText="Create"
      formId={formId}
      wrapProps={{ "data-test": "CreateUserDialog" }}>
      <ModalSection title="Account details">
        <DynamicForm id={formId} fields={formFields} onSubmit={handleSubmit} hideSubmitButton />
      </ModalSection>
      {error && <Alert message={error.message} type="error" showIcon data-test="CreateUserErrorAlert" className="m-t-15" />}
    </ModalShell>
  );
}

CreateUserDialog.propTypes = {
  dialog: DialogPropType.isRequired,
};

export default wrapDialog(CreateUserDialog);
