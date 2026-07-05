import theme from "antd/lib/theme";

import { getResolvedTheme } from "@/services/theme";

/** Map Rewatch design tokens to antd 5/6 theme config. */
export function buildAntdTheme(resolved = getResolvedTheme()) {
  const isDark = resolved === "dark";

  return {
    algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
    token: {
      colorPrimary: "#ff7230",
      colorInfo: "#0ea5b7",
      colorSuccess: "#16a34a",
      colorWarning: "#eab308",
      colorError: "#dc2626",
      colorLink: "#ff7230",
      colorLinkHover: "#f05a12",
      colorLinkActive: "#d3490a",
      borderRadius: 8,
      borderRadiusSM: 6,
      borderRadiusLG: 14,
      fontFamily:
        '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, system-ui, sans-serif',
      fontFamilyCode:
        '"JetBrains Mono", "SF Mono", ui-monospace, Menlo, Consolas, "Liberation Mono", monospace',
      fontSize: 14,
      colorBgContainer: isDark ? "#1a1612" : "#ffffff",
      colorBgElevated: isDark ? "#1f1a16" : "#ffffff",
      colorBgLayout: isDark ? "#100d0a" : "#faf8f5",
      colorBorder: isDark ? "#2e2620" : "#ece8e1",
      colorText: isDark ? "#f3eee8" : "#1f1a16",
      colorTextSecondary: isDark ? "#d6cfc7" : "#524a42",
      colorTextTertiary: isDark ? "#a59c91" : "#7a7068",
      zIndexPopupBase: 2000,
    },
    components: {
      Modal: {
        zIndexPopupBase: 2000,
      },
      Drawer: {
        zIndexPopupBase: 2000,
      },
      Message: {
        zIndexPopup: 2010,
      },
      Notification: {
        zIndexPopup: 2010,
      },
      Popover: {
        zIndexPopup: 2030,
      },
      Dropdown: {
        zIndexPopup: 2050,
      },
      DatePicker: {
        zIndexPopup: 2050,
      },
      Tooltip: {
        zIndexPopup: 2060,
      },
      Menu: {
        itemBg: "transparent",
        subMenuItemBg: isDark ? "#1f1a16" : "#ffffff",
        popupBg: isDark ? "#1f1a16" : "#ffffff",
        itemSelectedBg: isDark ? "rgba(255, 114, 48, 0.16)" : "rgba(255, 114, 48, 0.08)",
        itemHoverBg: isDark ? "rgba(255, 255, 255, 0.06)" : "rgba(0, 0, 0, 0.04)",
        horizontalItemSelectedColor: isDark ? "#f3eee8" : "#1f1a16",
        horizontalItemHoverColor: isDark ? "#f3eee8" : "#1f1a16",
      },
      Table: {
        headerBg: isDark ? "#1f1a16" : "#faf8f5",
        headerColor: isDark ? "#f3eee8" : "#1f1a16",
        rowHoverBg: isDark ? "rgba(255, 255, 255, 0.04)" : "rgba(0, 0, 0, 0.02)",
        borderColor: isDark ? "#2e2620" : "#ece8e1",
        colorText: isDark ? "#f3eee8" : "#1f1a16",
        colorTextHeading: isDark ? "#f3eee8" : "#1f1a16",
        colorBgContainer: isDark ? "#1a1612" : "#ffffff",
        footerBg: isDark ? "#1a1612" : "#ffffff",
        headerSplitColor: isDark ? "#241e19" : "#ece8e1",
      },
      Pagination: {
        itemBg: isDark ? "#1f1a16" : "#ffffff",
        itemActiveBg: "#ff7230",
        itemActiveColor: "#ffffff",
        itemLinkBg: isDark ? "#1f1a16" : "#ffffff",
        colorText: isDark ? "#d6cfc7" : "#524a42",
        colorPrimary: "#ff7230",
        colorPrimaryHover: "#f05a12",
      },
      Typography: {
        colorText: isDark ? "#f3eee8" : "#1f1a16",
        colorTextSecondary: isDark ? "#d6cfc7" : "#524a42",
        colorTextDescription: isDark ? "#a59c91" : "#7a7068",
      },
      List: {
        colorText: isDark ? "#f3eee8" : "#1f1a16",
        colorTextDescription: isDark ? "#a59c91" : "#7a7068",
      },
      Select: {
        optionSelectedBg: isDark ? "rgba(255, 114, 48, 0.16)" : "rgba(255, 114, 48, 0.08)",
      },
    },
  };
}
