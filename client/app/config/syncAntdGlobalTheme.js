import ConfigProvider from "antd/lib/config-provider";

import { buildAntdTheme } from "@/config/antdTheme";
import { getResolvedTheme } from "@/services/theme";

/** Keep antd static APIs (Modal.confirm, message, etc.) in sync with the active theme. */
export function syncAntdGlobalTheme(resolved = getResolvedTheme()) {
  ConfigProvider.config({ theme: buildAntdTheme(resolved) });
}
