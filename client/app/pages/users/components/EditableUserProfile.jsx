import React, { useState, useEffect } from "react";
import { UserProfile } from "@/components/proptypes";

import UserInfoForm from "./UserInfoForm";
import ProfileImageForm from "./ProfileImageForm";
import ApiKeyForm from "./ApiKeyForm";
import PasswordForm from "./PasswordForm";
import ToggleUserForm from "./ToggleUserForm";

export default function EditableUserProfile(props) {
  const [user, setUser] = useState(props.user);

  useEffect(() => {
    setUser(props.user);
  }, [props.user]);

  return (
    <div className="col-md-4 col-md-offset-4">
      {user.isDisabled ? (
        <React.Fragment>
          <img alt="Profile" src={user.profileImageUrl} className="profile__image" width="40" />
          <h3 className="profile__h3">{user.name}</h3>
        </React.Fragment>
      ) : (
        <React.Fragment>
          <ProfileImageForm user={user} onChange={setUser} />
          <h3 className="profile__h3 text-center">{user.name}</h3>
        </React.Fragment>
      )}
      <hr />
      <UserInfoForm user={user} onChange={setUser} />
      {!user.isDisabled && (
        <React.Fragment>
          <ApiKeyForm user={user} onChange={setUser} />
          <hr />
          <PasswordForm user={user} />
        </React.Fragment>
      )}
      <hr />
      <ToggleUserForm user={user} onChange={setUser} />
    </div>
  );
}

EditableUserProfile.propTypes = {
  user: UserProfile.isRequired,
};
