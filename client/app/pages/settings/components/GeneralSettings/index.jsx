import React from "react";
import DynamicComponent from "@/components/DynamicComponent";
import SettingsSection from "./SettingsSection";

import FormatSettings from "./FormatSettings";
import ChartSettings from "./ChartSettings";
import FeatureFlagsSettings from "./FeatureFlagsSettings";

export default function GeneralSettings(props) {
  return (
    <DynamicComponent name="OrganizationSettings.GeneralSettings" {...props}>
      <SettingsSection
        title="General"
        description="Defaults used across queries, dashboards, and visualizations in this organization.">
        <FormatSettings {...props} />
        <ChartSettings {...props} />
        <FeatureFlagsSettings {...props} />
      </SettingsSection>
    </DynamicComponent>
  );
}
