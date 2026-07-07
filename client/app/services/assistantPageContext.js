import location from "@/services/location";

const ID_FIELDS = [
  ["query_id", "queryId"],
  ["dashboard_id", "dashboardId"],
  ["alert_id", "alertId"],
  ["data_source_id", "dataSourceId"],
  ["model_id", "modelId"],
  ["indexer_id", "indexerId"],
  ["destination_id", "destinationId"],
  ["prediction_id", "predictionId"],
  ["user_id", "userId"],
  ["group_id", "groupId"],
];

const ROUTE_VIEWS = {
  "Queries.Source": "source_editor",
  "Queries.New": "new",
  "Alerts.New": "new",
  "Alerts.Edit": "edit",
  "MLModels.New": "new",
};

function parseId(value) {
  if (value == null || value === "") {
    return null;
  }
  const asNumber = Number.parseInt(String(value), 10);
  return Number.isNaN(asNumber) ? value : asNumber;
}

/** Build page context sent with each assistant chat turn. */
export function buildAssistantPageContext(currentRoute) {
  if (!currentRoute) {
    return null;
  }

  const params = currentRoute.routeParams || {};
  const context = {
    path: location.path,
    route_id: currentRoute.id || null,
    page_title: currentRoute.title || null,
  };

  ID_FIELDS.forEach(([outKey, paramKey]) => {
    const parsed = parseId(params[paramKey]);
    if (parsed != null) {
      context[outKey] = parsed;
    }
  });

  const view = ROUTE_VIEWS[currentRoute.id];
  if (view) {
    context.view = view;
  }

  const hasResource = ID_FIELDS.some(([outKey]) => context[outKey] != null);
  if (!context.route_id && !hasResource) {
    return context.path ? context : null;
  }

  return context;
}
