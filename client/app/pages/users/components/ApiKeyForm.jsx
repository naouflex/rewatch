import React, { useState, useCallback } from "react";
import PropTypes from "prop-types";
import Button from "antd/lib/button";
import Form from "antd/lib/form";
import { confirmDialog } from "@/components/ModalShell/confirmDialog";
import DynamicComponent from "@/components/DynamicComponent";
import InputWithCopy from "@/components/InputWithCopy";
import { UserProfile } from "@/components/proptypes";
import User from "@/services/user";
import useImmutableCallback from "@/lib/hooks/useImmutableCallback";
import { useUniqueId } from "@/lib/hooks/useUniqueId";

export default function ApiKeyForm(props) {
  const { user, onChange } = props;

  const [loading, setLoading] = useState(false);
  const handleChange = useImmutableCallback(onChange);
  const apiKeyInputId = useUniqueId("apiKey");

  const regenerateApiKey = useCallback(() => {
    const doRegenerate = () => {
      setLoading(true);
      User.regenerateApiKey(user)
        .then(apiKey => {
          if (apiKey) {
            handleChange({ ...user, apiKey });
          }
        })
        .finally(() => {
          setLoading(false);
        });
    };

    confirmDialog({
      title: "Regenerate API Key",
      description: "Are you sure you want to regenerate?",
      okText: "Regenerate",
      onConfirm: doRegenerate,
    });
  }, [user, handleChange]);

  return (
    <DynamicComponent name="UserProfile.ApiKeyForm" {...props}>
      <Form layout="vertical">
        <hr />
        <Form.Item label="API Key" className="m-b-10">
          <InputWithCopy id={apiKeyInputId} className="hide-in-percy" value={user.apiKey} data-test="ApiKey" readOnly />
        </Form.Item>
        <Button className="w-100" onClick={regenerateApiKey} loading={loading} data-test="RegenerateApiKey">
          Regenerate
        </Button>
      </Form>
    </DynamicComponent>
  );
}

ApiKeyForm.propTypes = {
  user: UserProfile.isRequired,
  onChange: PropTypes.func,
};

ApiKeyForm.defaultProps = {
  onChange: () => {},
};
