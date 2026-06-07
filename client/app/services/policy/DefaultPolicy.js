import { get, isArray } from "lodash";
import { currentUser, clientConfig } from "@/services/auth";

/* eslint-disable class-methods-use-this */

export default class DefaultPolicy {
  refresh() {
    return Promise.resolve(this);
  }

  canCreateDataSource() {
    return currentUser.isAdmin;
  }

  isCreateDataSourceEnabled() {
    return currentUser.isAdmin;
  }

  canCreateDestination() {
    return currentUser.hasPermission("create_destination");
  }

  isCreateDestinationEnabled() {
    return currentUser.hasPermission("create_destination");
  }

  canCreateDashboard() {
    return currentUser.hasPermission("create_dashboard");
  }

  isCreateDashboardEnabled() {
    return currentUser.hasPermission("create_dashboard");
  }

  canCreateAlert() {
    return true;
  }

  canCreateUser() {
    return currentUser.isAdmin;
  }

  isCreateUserEnabled() {
    return currentUser.isAdmin;
  }

  isCreateQuerySnippetEnabled() {
    return currentUser.hasPermission("create_query_snippet");
  }

  getDashboardRefreshIntervals() {
    const result = clientConfig.dashboardRefreshIntervals;
    return isArray(result) ? result : null;
  }

  getQueryRefreshIntervals() {
    const result = clientConfig.queryRefreshIntervals;
    return isArray(result) ? result : null;
  }

  canEdit(object) {
    return get(object, "can_edit", false);
  }

  canRun() {
    return true;
  }
}
