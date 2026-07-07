import React, { useMemo, useReducer, useEffect } from "react";
import { first, includes } from "lodash";
import Menu from "antd/lib/menu";
import Link from "@/components/Link";
import PlainButton from "@/components/PlainButton";
import HelpTrigger from "@/components/HelpTrigger";
import { useCurrentRoute } from "@/components/ApplicationArea/Router";
import { Auth, clientConfig, currentUser, subscribeToCurrentUser } from "@/services/auth";
import settingsMenu from "@/services/settingsMenu";
import { APPLICATION_TITLE } from "@/config/brand";
import logoUrl from "@/assets/images/icon_small.png";

import ThemeToggle from "@/components/ThemeToggle";
import VersionInfo from "./VersionInfo";

import "./DesktopNavbar.less";

function NavbarSection({ items, className, ...props }) {
  return (
    <Menu
      selectable={false}
      mode="horizontal"
      className={`desktop-navbar-menu ${className || ""}`}
      items={items}
      {...props}
    />
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
          "QuerySnippets.List",
          "QuerySnippets.My",
          "QuerySnippets.Favorites",
          "QuerySnippets.Archived",
          "QuerySnippets.NewOrEdit",
        ],
        currentRoute.id
      ),
      dataSources: includes(["DataSources.List"], currentRoute.id),
      assistant: currentRoute.id === "Assistant",
      community: includes(["Community.List", "Community.View", "Community.New"], currentRoute.id),
      apiDocs: currentRoute.id === "ApiDocs",
      alerts: includes(
        [
          "Alerts.List",
          "Alerts.New",
          "Alerts.View",
          "Alerts.Edit",
          "AlertEvents.List",
          "AlertDestinations.List",
          "AlertDestinations.My",
          "AlertDestinations.Favorites",
          "AlertDestinations.Archived",
          "AlertDestinations.New",
          "AlertDestinations.Edit",
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
      models: includes(
        [
          "MLModels.List",
          "MLModels.My",
          "MLModels.Favorites",
          "MLModels.Archive",
          "MLModels.New",
          "MLModels.View",
          "MLModels.Edit",
          "MLModels.Stats",
          "MLModels.Overview",
          "MLModels.Predictions",
          "MLModels.Versions",
          "MLModels.Metrics",
          "MLModels.MetricsHistory",
          "MLModels.MetricsHistoryTrain",
          "MLModelsVersions.List",
          "MLModelsVersions.My",
          "MLModelsVersions.Favorites",
          "MLModelsVersions.Archive",
          "MLModelsVersions.View",
          "PredictionResults.List",
          "PredictionResults.My",
          "PredictionResults.Favorites",
          "PredictionResults.Archive",
          "PredictionResult.View",
        ],
        currentRoute.id
      ),
    }),
    [currentRoute.id]
  );
}

export default function DesktopNavbar() {
  const firstSettingsTab = first(settingsMenu.getAvailableItems());

  const [, forceUpdate] = useReducer(x => x + 1, 0);
  useEffect(() => subscribeToCurrentUser(forceUpdate), []);

  const activeState = useNavbarActiveState();

  const canListModels = currentUser.hasPermission("list_models");

  const mainNavItems = useMemo(() => {
    const items = [];

    if (currentUser.hasPermission("list_dashboards")) {
      items.push({
        key: "dashboards",
        className: activeState.dashboards ? "navbar-active-item" : null,
        label: (
          <Link href="dashboards">
            <span className="desktop-navbar-label">Dashboards</span>
          </Link>
        ),
      });
    }

    if (currentUser.hasPermission("view_query")) {
      items.push({
        key: "queries",
        popupClassName: "desktop-navbar-submenu",
        className: activeState.queries ? "navbar-active-item" : null,
        label: (
          <Link href="queries" className="navbar-submenu-title">
            <span className="desktop-navbar-label">Queries</span>
          </Link>
        ),
        children: [
          {
            key: "queries-list",
            label: <Link href="queries">Queries</Link>,
          },
          ...(currentUser.hasPermission("list_query_snippets")
            ? [
                {
                  key: "query-snippets",
                  label: <Link href="query_snippets">Query Snippets</Link>,
                },
              ]
            : []),
        ],
      });
    }

    if (currentUser.hasPermission("list_alerts")) {
      items.push({
        key: "alerts",
        popupClassName: "desktop-navbar-submenu",
        className: activeState.alerts ? "navbar-active-item" : null,
        label: (
          <Link href="alerts" className="navbar-submenu-title">
            <span className="desktop-navbar-label">Alerts</span>
          </Link>
        ),
        children: [
          {
            key: "alerts-list",
            label: <Link href="alerts">Alerts</Link>,
          },
          {
            key: "alerts-history",
            label: <Link href="alert_events">Alerts History</Link>,
          },
          ...(currentUser.hasPermission("list_destinations")
            ? [
                {
                  key: "alert-destinations",
                  label: <Link href="destinations">Destinations</Link>,
                },
              ]
            : []),
        ],
      });
    }

    if (currentUser.hasPermission("list_indexers")) {
      items.push({
        key: "indexers",
        className: activeState.indexers ? "navbar-active-item" : null,
        label: (
          <Link href="indexers">
            <span className="desktop-navbar-label">Indexers</span>
          </Link>
        ),
      });
    }

    if (canListModels) {
      items.push({
        key: "models",
        popupClassName: "desktop-navbar-submenu",
        className: activeState.models ? "navbar-active-item" : null,
        label: (
          <Link href="ml_models" className="navbar-submenu-title">
            <span className="desktop-navbar-label">Models</span>
          </Link>
        ),
        children: [
          {
            key: "models-list",
            label: <Link href="ml_models">Models</Link>,
          },
          {
            key: "models-versions",
            label: <Link href="ml_models_versions">Versions</Link>,
          },
          {
            key: "predictions-list",
            label: <Link href="predictions">Predictions</Link>,
          },
        ],
      });
    }

    if (clientConfig.assistantEnabled) {
      items.push({
        key: "assistant",
        className: activeState.assistant ? "navbar-active-item" : null,
        label: (
          <Link href="assistant">
            <span className="desktop-navbar-label">Assistant</span>
          </Link>
        ),
      });
    }

    if (currentUser.hasPermission("list_community_posts")) {
      items.push({
        key: "community",
        className: activeState.community ? "navbar-active-item" : null,
        label: (
          <Link href="community">
            <span className="desktop-navbar-label">Community</span>
          </Link>
        ),
      });
    }

    items.push({
      key: "api-docs",
      className: activeState.apiDocs ? "navbar-active-item" : null,
      label: (
        <Link href="api-docs">
          <span className="desktop-navbar-label">API</span>
        </Link>
      ),
    });

    return items;
  }, [activeState, canListModels]);

  const utilityNavItems = useMemo(() => {
    const items = [];

    items.push({
      key: "theme",
      className: "desktop-navbar-theme-item",
      "data-test": "ThemeToggle",
      label: <ThemeToggle />,
    });

    items.push({
      key: "profile",
      popupClassName: "desktop-navbar-submenu",
      className: "desktop-navbar-profile-menu",
      tabIndex: 0,
      label: (
        <span data-test="ProfileDropdown" className="desktop-navbar-profile-menu-title">
          <img className="profile__image_thumb" src={currentUser.profile_image_url} alt={currentUser.name} />
        </span>
      ),
      children: [
        {
          key: "profile",
          label: <Link href="users/me">Profile</Link>,
        },
        {
          key: "help",
          className: "desktop-navbar-profile-menu-item",
          label: (
            <HelpTrigger showTooltip={false} type="HOME" tabIndex={0}>
              Help
            </HelpTrigger>
          ),
        },
        ...(firstSettingsTab
          ? [
              {
                key: "settings",
                label: (
                  <Link href={firstSettingsTab.path} data-test="SettingsLink">
                    Settings
                  </Link>
                ),
              },
            ]
          : []),
        ...(currentUser.hasPermission("super_admin")
          ? [
              {
                key: "status",
                label: <Link href="admin/status">System Status</Link>,
              },
            ]
          : []),
        { type: "divider" },
        {
          key: "logout",
          label: (
            <PlainButton data-test="LogOutButton" onClick={() => Auth.logout()}>
              Log out
            </PlainButton>
          ),
        },
        { type: "divider" },
        {
          key: "version",
          role: "presentation",
          disabled: true,
          className: "version-info",
          label: <VersionInfo />,
        },
      ],
    });

    return items;
  }, [firstSettingsTab]);

  return (
    <nav className="desktop-navbar">
      <div className="desktop-navbar-logo">
        <Link href="./" className="desktop-navbar-logo-link">
          <img src={logoUrl} alt="" />
          <span className="desktop-navbar-logo-title">{APPLICATION_TITLE}</span>
        </Link>
      </div>

      <NavbarSection className="desktop-navbar-main" items={mainNavItems} />

      <NavbarSection className="desktop-navbar-utilities" items={utilityNavItems} />
    </nav>
  );
}
