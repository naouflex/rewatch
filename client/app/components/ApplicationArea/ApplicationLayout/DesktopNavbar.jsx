import React, { useMemo } from "react";
import { first, includes } from "lodash";
import Menu from "antd/lib/menu";
import Link from "@/components/Link";
import PlainButton from "@/components/PlainButton";
import HelpTrigger from "@/components/HelpTrigger";
import CreateDashboardDialog from "@/components/dashboards/CreateDashboardDialog";
import { useCurrentRoute } from "@/components/ApplicationArea/Router";
import { Auth, currentUser } from "@/services/auth";
import settingsMenu from "@/services/settingsMenu";
import logoUrl from "@/assets/images/icon_small.png";

import DesktopOutlinedIcon from "@ant-design/icons/DesktopOutlined";
import CodeOutlinedIcon from "@ant-design/icons/CodeOutlined";
import AlertOutlinedIcon from "@ant-design/icons/AlertOutlined";
import DatabaseOutlinedIcon from "@ant-design/icons/DatabaseOutlined";
import PlusOutlinedIcon from "@ant-design/icons/PlusOutlined";
import QuestionCircleOutlinedIcon from "@ant-design/icons/QuestionCircleOutlined";
import SettingOutlinedIcon from "@ant-design/icons/SettingOutlined";
import ThemeToggle from "@/components/ThemeToggle";
import VersionInfo from "./VersionInfo";

import "./DesktopNavbar.less";

function NavbarSection({ children, ...props }) {
  return (
    <Menu selectable={false} mode="vertical" {...props}>
      {children}
    </Menu>
  );
}

function useNavbarActiveState() {
  const currentRoute = useCurrentRoute();

  return useMemo(
    () => ({
      dashboards: includes(
        [
          "Dashboards.List",
          "Dashboards.Favorites",
          "Dashboards.My",
          "Dashboards.ViewOrEdit",
          "Dashboards.LegacyViewOrEdit",
        ],
        currentRoute.id
      ),
      queries: includes(
        [
          "Queries.List",
          "Queries.Favorites",
          "Queries.Archived",
          "Queries.My",
          "Queries.View",
          "Queries.New",
          "Queries.Edit",
        ],
        currentRoute.id
      ),
      dataSources: includes(["DataSources.List"], currentRoute.id),
      alerts: includes(
        [
          "Alerts.List",
          "Alerts.New",
          "Alerts.View",
          "Alerts.Edit",
          "AlertEvents.List",
        ],
        currentRoute.id
      ),
      indexers: includes(
        [
          "Indexers.List",
          "Indexers.My",
          "Indexers.Favorites",
          "Indexers.Archived",
          "Indexers.New",
          "Indexers.View",
          "Indexers.Edit",
        ],
        currentRoute.id
      ),
    }),
    [currentRoute.id]
  );
}

export default function DesktopNavbar() {
  const firstSettingsTab = first(settingsMenu.getAvailableItems());

  const activeState = useNavbarActiveState();

  const canCreateQuery = currentUser.hasPermission("create_query");
  const canCreateDashboard = currentUser.hasPermission("create_dashboard");
  const canCreateAlert = currentUser.hasPermission("list_alerts");
  const canCreateIndexer = currentUser.hasPermission("create_indexer");

  return (
    <nav className="desktop-navbar">
      <NavbarSection className="desktop-navbar-logo">
        <div role="menuitem">
          <Link href="./">
            <img src={logoUrl} alt="Redash" />
          </Link>
        </div>
      </NavbarSection>

      <NavbarSection>
        {currentUser.hasPermission("list_dashboards") && (
          <Menu.Item key="dashboards" className={activeState.dashboards ? "navbar-active-item" : null}>
            <Link href="dashboards">
              <DesktopOutlinedIcon aria-label="Dashboard navigation button" />
              <span className="desktop-navbar-label">Dashboards</span>
            </Link>
          </Menu.Item>
        )}
        {currentUser.hasPermission("view_query") && (
          <Menu.Item key="queries" className={activeState.queries ? "navbar-active-item" : null}>
            <Link href="queries">
              <CodeOutlinedIcon aria-label="Queries navigation button" />
              <span className="desktop-navbar-label">Queries</span>
            </Link>
          </Menu.Item>
        )}
        {currentUser.hasPermission("list_alerts") && (
          <Menu.SubMenu
            key="alerts"
            popupClassName="desktop-navbar-submenu"
            className={activeState.alerts ? "navbar-active-item" : null}
            title={
              <Link href="alerts" className="navbar-submenu-title">
                <AlertOutlinedIcon aria-label="Alerts navigation button" />
                <span className="desktop-navbar-label">Alerts</span>
              </Link>
            }>
            <Menu.Item key="alerts-list">
              <Link href="alerts">Alerts</Link>
            </Menu.Item>
            <Menu.Item key="alerts-history">
              <Link href="alert_events">Alerts History</Link>
            </Menu.Item>
          </Menu.SubMenu>
        )}
        {currentUser.hasPermission("list_indexers") && (
          <Menu.Item key="indexers" className={activeState.indexers ? "navbar-active-item" : null}>
            <Link href="indexers">
              <DatabaseOutlinedIcon aria-label="Indexers navigation button" />
              <span className="desktop-navbar-label">Indexers</span>
            </Link>
          </Menu.Item>
        )}
      </NavbarSection>

      <NavbarSection className="desktop-navbar-spacer">
        {(canCreateQuery || canCreateDashboard || canCreateAlert || canCreateIndexer) && (
          <Menu.SubMenu
            key="create"
            popupClassName="desktop-navbar-submenu"
            data-test="CreateButton"
            tabIndex={0}
            title={
              <React.Fragment>
                <PlusOutlinedIcon />
                <span className="desktop-navbar-label">Create</span>
              </React.Fragment>
            }>
            {canCreateQuery && (
              <Menu.Item key="new-query">
                <Link href="queries/new" data-test="CreateQueryMenuItem">
                  New Query
                </Link>
              </Menu.Item>
            )}
            {canCreateDashboard && (
              <Menu.Item key="new-dashboard">
                <PlainButton data-test="CreateDashboardMenuItem" onClick={() => CreateDashboardDialog.showModal()}>
                  New Dashboard
                </PlainButton>
              </Menu.Item>
            )}
            {canCreateAlert && (
              <Menu.Item key="new-alert">
                <Link data-test="CreateAlertMenuItem" href="alerts/new">
                  New Alert
                </Link>
              </Menu.Item>
            )}
            {canCreateIndexer && (
              <Menu.Item key="new-indexer">
                <Link data-test="CreateIndexerMenuItem" href="indexers/new">
                  New Indexer
                </Link>
              </Menu.Item>
            )}
          </Menu.SubMenu>
        )}
      </NavbarSection>

      <NavbarSection>
        <Menu.Item key="help">
          <HelpTrigger showTooltip={false} type="HOME" tabIndex={0}>
            <QuestionCircleOutlinedIcon />
            <span className="desktop-navbar-label">Help</span>
          </HelpTrigger>
        </Menu.Item>
        {firstSettingsTab && (
          <Menu.Item key="settings" className={activeState.dataSources ? "navbar-active-item" : null}>
            <Link href={firstSettingsTab.path} data-test="SettingsLink">
              <SettingOutlinedIcon />
              <span className="desktop-navbar-label">Settings</span>
            </Link>
          </Menu.Item>
        )}
        

        <Menu.Item key="theme" className="desktop-navbar-theme-item" data-test="ThemeToggle">
          <ThemeToggle />
        </Menu.Item>
      </NavbarSection>

      <NavbarSection className="desktop-navbar-profile-menu">
        <Menu.SubMenu
          key="profile"
          popupClassName="desktop-navbar-submenu"
          tabIndex={0}
          title={
            <span data-test="ProfileDropdown" className="desktop-navbar-profile-menu-title">
              <img className="profile__image_thumb" src={currentUser.profile_image_url} alt={currentUser.name} />
            </span>
          }>
          <Menu.Item key="profile">
            <Link href="users/me">Profile</Link>
          </Menu.Item>
          {currentUser.hasPermission("super_admin") && (
            <Menu.Item key="status">
              <Link href="admin/status">System Status</Link>
            </Menu.Item>
          )}
          <Menu.Divider />
          <Menu.Item key="logout">
            <PlainButton data-test="LogOutButton" onClick={() => Auth.logout()}>
              Log out
            </PlainButton>
          </Menu.Item>
          <Menu.Divider />
          <Menu.Item key="version" role="presentation" disabled className="version-info">
            <VersionInfo />
          </Menu.Item>
        </Menu.SubMenu>
      </NavbarSection>
    </nav>
  );
}
