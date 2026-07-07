import { get, startsWith } from "lodash";
import React, { useState, useCallback } from "react";
import PropTypes from "prop-types";
import Button from "antd/lib/button";
import Upload from "antd/lib/upload";
import CameraOutlinedIcon from "@ant-design/icons/CameraOutlined";
import LoadingOutlinedIcon from "@ant-design/icons/LoadingOutlined";

import DataSource, { getDataSourceIconUrl } from "@/services/data-source";
import notification from "@/services/notification";

const IMAGE_SIZE = 64;
const MAX_FILE_SIZE = 5 * 1024 * 1024;

function resizeImageFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Could not read the selected file."));
    reader.onload = () => {
      const image = new Image();
      image.onerror = () => reject(new Error("The selected file is not a valid image."));
      image.onload = () => {
        const canvas = document.createElement("canvas");
        canvas.width = IMAGE_SIZE;
        canvas.height = IMAGE_SIZE;
        const context = canvas.getContext("2d");
        const scale = Math.max(IMAGE_SIZE / image.width, IMAGE_SIZE / image.height);
        const width = image.width * scale;
        const height = image.height * scale;
        context.drawImage(image, (IMAGE_SIZE - width) / 2, (IMAGE_SIZE - height) / 2, width, height);
        resolve(canvas.toDataURL("image/png"));
      };
      image.src = reader.result;
    };
    reader.readAsDataURL(file);
  });
}

export default function DataSourceIconForm({ dataSource, onChange }) {
  const [uploading, setUploading] = useState(false);

  const saveIcon = useCallback(
    iconUrl => {
      setUploading(true);
      return DataSource.save({ ...dataSource, icon_url: iconUrl || null })
        .then(updatedDataSource => {
          notification.success(iconUrl ? "Data source logo updated." : "Data source logo reset to default.");
          onChange(updatedDataSource);
        })
        .catch(error => {
          notification.error(
            "Failed to update data source logo.",
            get(error, "response.data.message", "Please try again.")
          );
        })
        .finally(() => setUploading(false));
    },
    [dataSource, onChange]
  );

  const beforeUpload = useCallback(
    file => {
      if (!startsWith(file.type, "image/")) {
        notification.error("Please select an image file.");
        return false;
      }
      if (file.size > MAX_FILE_SIZE) {
        notification.error("Please select an image smaller than 5MB.");
        return false;
      }
      resizeImageFile(file)
        .then(saveIcon)
        .catch(() => notification.error("Failed to process the selected image."));
      return false;
    },
    [saveIcon]
  );

  const hasCustomIcon = startsWith(dataSource.icon_url, "data:");

  return (
    <div className="datasource__icon-form">
      <Upload accept="image/*" showUploadList={false} beforeUpload={beforeUpload} disabled={uploading}>
        <div className="datasource__icon-wrapper" role="button" tabIndex={0} title="Change logo">
          <img
            alt={dataSource.name}
            src={getDataSourceIconUrl(dataSource)}
            className="datasource__icon-image"
            width={IMAGE_SIZE}
            height={IMAGE_SIZE}
          />
          <div className="datasource__icon-overlay">
            {uploading ? <LoadingOutlinedIcon /> : <CameraOutlinedIcon />}
            <span>{uploading ? "Uploading…" : "Change"}</span>
          </div>
        </div>
      </Upload>
      {hasCustomIcon && (
        <div className="datasource__icon-actions">
          <Button type="link" size="small" disabled={uploading} onClick={() => saveIcon("")}>
            Reset to default
          </Button>
        </div>
      )}
    </div>
  );
}

DataSourceIconForm.propTypes = {
  dataSource: PropTypes.shape({
    id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired,
    type: PropTypes.string.isRequired,
    options: PropTypes.object,
    icon_url: PropTypes.string,
  }).isRequired,
  onChange: PropTypes.func,
};

DataSourceIconForm.defaultProps = {
  onChange: () => {},
};
