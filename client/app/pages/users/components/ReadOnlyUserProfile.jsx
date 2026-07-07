import React from "react";
import { UserProfile } from "@/components/proptypes";
import UserGroups from "@/components/UserGroups";

import useUserGroups from "../hooks/useUserGroups";

import "@/components/items-list/create-page-layout.less";

export default function ReadOnlyUserProfile({ user }) {
  const { groups, isLoading: isLoadingGroups } = useUserGroups(user);

  return (
    <div className="settings-detail-form">
      <div className="create-page-form__body profile__container">
      <img alt="profile" src={user.profileImageUrl} className="profile__image" width="40" />
      <h3 className="profile__h3">{user.name}</h3>
      <hr />
      <dl className="profile__dl">
        <dt>Name:</dt>
        <dd>{user.name}</dd>
        <dt>Email:</dt>
        <dd>{user.email}</dd>
        <dt className="m-b-5">Groups:</dt>
        <dd>{isLoadingGroups ? "Loading..." : <UserGroups groups={groups} />}</dd>
      </dl>
      </div>
    </div>
  );
}

ReadOnlyUserProfile.propTypes = {
  user: UserProfile.isRequired,
};
