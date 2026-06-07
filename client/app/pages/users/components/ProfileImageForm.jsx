import { get, startsWith } from "lodash";
import React, { useState, useCallback } from "react";
import PropTypes from "prop-types";
import Button from "antd/lib/button";
import Upload from "antd/lib/upload";
import CameraOutlinedIcon from "@ant-design/icons/CameraOutlined";
import LoadingOutlinedIcon from "@ant-design/icons/LoadingOutlined";

import { UserProfile } from "@/components/proptypes";
import User from "@/services/user";
import { currentUser, updateCurrentUser } from "@/services/auth";
import notification from "@/services/notification";

const IMAGE_SIZE = 96;
const MAX_FILE_SIZE = 5 * 1024 * 1024;

// Reads the selected file and renders it into a small square canvas so we only
// ever store/upload a tiny avatar (a few KB) regardless of the original size.
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

export default function ProfileImageForm({ user, onChange }) {
  const [uploading, setUploading] = useState(false);

  const saveImage = useCallback(
    profileImageUrl => {
      setUploading(true);
      return User.save({ id: user.id, profile_image_url: profileImageUrl })
        .then(updatedUser => {
          notification.success(profileImageUrl ? "Profile picture updated." : "Profile picture removed.");
          onChange(User.convertUserInfo(updatedUser));
          // Refresh the in-memory current user so the navbar avatar (and any
          // other place using `currentUser`) updates without a page reload.
          if (currentUser.id === updatedUser.id) {
            updateCurrentUser({ profile_image_url: updatedUser.profile_image_url });
          }
        })
        .catch(error => {
          notification.error(
            "Failed to update profile picture.",
            get(error, "response.data.message", "Please try again.")
          );
        })
        .finally(() => setUploading(false));
    },
    [user.id, onChange]
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
        .then(saveImage)
        .catch(() => notification.error("Failed to process the selected image."));
      return false;
    },
    [saveImage]
  );

  const hasCustomImage = startsWith(user.profileImageUrl, "data:");

  return (
    <div className="profile__image-form">
      <Upload accept="image/*" showUploadList={false} beforeUpload={beforeUpload} disabled={uploading}>
        <div className="profile__avatar-wrapper" role="button" tabIndex={0} title="Change picture">
          <img
            alt="Profile"
            src={user.profileImageUrl}
            className="profile__image-large"
            width={IMAGE_SIZE}
            height={IMAGE_SIZE}
          />
          <div className="profile__avatar-overlay">
            {uploading ? <LoadingOutlinedIcon /> : <CameraOutlinedIcon />}
            <span>{uploading ? "Uploading…" : "Change"}</span>
          </div>
        </div>
      </Upload>
      {hasCustomImage && (
        <div className="profile__image-actions">
          <Button type="link" size="small" disabled={uploading} onClick={() => saveImage("")}>
            Remove photo
          </Button>
        </div>
      )}
    </div>
  );
}

ProfileImageForm.propTypes = {
  user: UserProfile.isRequired,
  onChange: PropTypes.func,
};

ProfileImageForm.defaultProps = {
  onChange: () => {},
};
