import { map, trim, uniq, compact } from "lodash";
import React, { useState, useEffect, useRef } from "react";
import PropTypes from "prop-types";
import Form from "antd/lib/form";
import Select from "antd/lib/select";
import { wrap as wrapDialog, DialogPropType } from "@/components/DialogWrapper";
import { ModalShell } from "@/components/ModalShell";
import { getModalFormProps } from "@/styles/formStyle";

function EditTagsDialog({ dialog, tags, getAvailableTags }) {
  const [availableTags, setAvailableTags] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [values, setValues] = useState(() => uniq(map(tags, trim)));
  const selectRef = useRef(null);

  useEffect(() => {
    if (selectRef.current && !isLoading) {
      selectRef.current.focus();
    }
  }, [isLoading]);

  useEffect(() => {
    let isCancelled = false;
    getAvailableTags().then(fetchedTags => {
      if (!isCancelled) {
        setAvailableTags(uniq(compact(map(fetchedTags, trim))));
        setIsLoading(false);
      }
    });
    return () => {
      isCancelled = true;
    };
  }, [getAvailableTags]);

  return (
    <ModalShell
      dialog={dialog}
      title="Add/Edit Tags"
      description="Type to add new tags or pick from existing ones."
      size="sm"
      okText="Save"
      onOk={() => dialog.close(values)}
      wrapProps={{ "data-test": "EditTagsDialog" }}>
      <Form {...getModalFormProps()}>
        <Form.Item label="Tags">
          <Select
            ref={selectRef}
            mode="tags"
            className="w-100"
            placeholder="Add some tags..."
            defaultValue={values}
            onChange={v => setValues(compact(map(v, trim)))}
            disabled={isLoading}
            loading={isLoading}
            size="large">
            {map(availableTags, tag => (
              <Select.Option key={tag}>{tag}</Select.Option>
            ))}
          </Select>
        </Form.Item>
      </Form>
    </ModalShell>
  );
}

EditTagsDialog.propTypes = {
  dialog: DialogPropType.isRequired,
  tags: PropTypes.arrayOf(PropTypes.string),
  getAvailableTags: PropTypes.func.isRequired,
};

EditTagsDialog.defaultProps = {
  tags: [],
};

export default wrapDialog(EditTagsDialog);
