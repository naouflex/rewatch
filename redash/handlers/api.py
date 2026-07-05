from flask import make_response
from flask_restful import Api
from werkzeug.wrappers import Response

from redash.handlers.alert_events import (
    AlertEventListResource,
    AlertEventResource,
    MyAlertEventsResource,
)
from redash.handlers.assistant import (
    AssistantChatResource,
    AssistantChatStreamResource,
    AssistantDashboardPreviewResource,
    AssistantGenerateQueryResource,
    AssistantQueryPreviewResource,
    AssistantStatusResource,
    AssistantThreadListResource,
    AssistantThreadMessagesResource,
    AssistantThreadResource,
    AssistantVisualizationPreviewResource,
)
from redash.handlers.alerts import (
    AlertArchiveResource,
    AlertArchivedListResource,
    AlertEvaluateResource,
    AlertFavoriteListResource,
    AlertFavoriteResource,
    AlertListResource,
    AlertMuteResource,
    AlertResource,
    AlertSubscriptionListResource,
    AlertSubscriptionResource,
    AlertTagsResource,
    MyAlertsResource,
)
from redash.handlers.base import org_scoped_rule
from redash.handlers.dashboards import (
    DashboardFavoriteListResource,
    DashboardForkResource,
    DashboardListResource,
    DashboardResource,
    DashboardShareResource,
    DashboardTagsResource,
    MyDashboardsResource,
    PublicDashboardResource,
)
from redash.handlers.data_sources import (
    DataSourceListResource,
    DataSourcePauseResource,
    DataSourceResource,
    DataSourceSchemaResource,
    DataSourceTestResource,
    DataSourceTypeListResource,
)
from redash.handlers.databricks import (
    DatabricksDatabaseListResource,
    DatabricksSchemaResource,
    DatabricksTableColumnListResource,
)
from redash.handlers.indexers import (
    IndexerArchiveResource,
    IndexerArchivedListResource,
    IndexerFavoriteListResource,
    IndexerFavoriteResource,
    IndexerListResource,
    IndexerResource,
    IndexerTagsResource,
    MyIndexersResource,
)
from redash.handlers.destinations import (
    DestinationArchiveResource,
    DestinationArchivedListResource,
    DestinationFavoriteListResource,
    DestinationFavoriteResource,
    DestinationListResource,
    DestinationResource,
    DestinationTagsResource,
    DestinationTypeListResource,
    MyDestinationsResource,
)
from redash.handlers.events import EventsResource
from redash.handlers.favorites import (
    DashboardFavoriteResource,
    MLModelFavoriteResource,
    MLModelVersionFavoriteResource,
    PredictionResultFavoriteResource,
    QueryFavoriteResource,
)
from redash.handlers.ml_models import (
    MLModelArchiveResource,
    MLModelCopyResource,
    MLModelCreateFromVersionResource,
    MLModelFavoriteListResource,
    MLModelListResource,
    MLModelMuteResource,
    MLModelPredictResource,
    MLModelRecentResource,
    MLModelResource,
    MLModelSearchResource,
    MLModelStopPredictResource,
    MLModelStopResource,
    MLModelSubscriptionListResource,
    MLModelSubscriptionResource,
    MLModelTagsResource,
    MLModelTrainResource,
    MLModelVersionRevertResource,
    MyMLModelsResource,
)
from redash.handlers.ml_model_versions import (
    MLModelVersionArchiveResource,
    MLModelVersionFavoriteListResource,
    MLModelVersionListResource,
    MLModelVersionRecentResource,
    MLModelVersionResource,
    MLModelVersionSearchResource,
    MLModelVersionTagsResource,
    ModelVersionsResource,
    MyMLModelVersionsResource,
)
from redash.handlers.prediction_results import (
    BasePredictionResultListResource,
    ModelPredictionsResource,
    MyPredictionResultsResource,
    PredictionResultArchiveResource,
    PredictionResultFavoriteListResource,
    PredictionResultListResource,
    PredictionResultRecentResource,
    PredictionResultResource,
    PredictionResultSearchResource,
    PredictionResultTagsResource,
)
from redash.handlers.groups import (
    GroupDataSourceListResource,
    GroupDataSourceResource,
    GroupListResource,
    GroupMemberListResource,
    GroupMemberResource,
    GroupResource,
)
from redash.handlers.permissions import (
    CheckPermissionResource,
    ObjectPermissionsListResource,
)
from redash.handlers.queries import (
    MyQueriesResource,
    QueryArchiveResource,
    QueryFavoriteListResource,
    QueryForkResource,
    QueryListResource,
    QueryRecentResource,
    QueryRefreshResource,
    QueryRegenerateApiKeyResource,
    QueryResource,
    QuerySearchResource,
    QueryTagsResource,
)
from redash.handlers.query_results import (
    JobResource,
    QueryDropdownsResource,
    QueryResultDropdownResource,
    QueryResultListResource,
    QueryResultResource,
)
from redash.handlers.query_snippets import (
    MyQuerySnippetsResource,
    QuerySnippetArchiveResource,
    QuerySnippetArchivedListResource,
    QuerySnippetFavoriteListResource,
    QuerySnippetFavoriteResource,
    QuerySnippetListResource,
    QuerySnippetResource,
    QuerySnippetTagsResource,
)
from redash.handlers.settings import OrganizationSettings
from redash.handlers.users import (
    UserDisableResource,
    UserInviteResource,
    UserListResource,
    UserRegenerateApiKeyResource,
    UserResetPasswordResource,
    UserResource,
)
from redash.handlers.visualizations import (
    VisualizationListResource,
    VisualizationResource,
)
from redash.handlers.widgets import WidgetListResource, WidgetResource
from redash.utils import json_dumps


class ApiExt(Api):
    def add_org_resource(self, resource, *urls, **kwargs):
        urls = [org_scoped_rule(url) for url in urls]
        return self.add_resource(resource, *urls, **kwargs)


api = ApiExt()


@api.representation("application/json")
def json_representation(data, code, headers=None):
    # Flask-Restful checks only for flask.Response but flask-login uses werkzeug.wrappers.Response
    if isinstance(data, Response):
        return data
    resp = make_response(json_dumps(data), code)
    resp.headers.extend(headers or {})
    return resp


api.add_org_resource(AlertResource, "/api/alerts/<alert_id>", endpoint="alert")
api.add_org_resource(AlertMuteResource, "/api/alerts/<alert_id>/mute", endpoint="alert_mute")
api.add_org_resource(AlertArchiveResource, "/api/alerts/<alert_id>/archive", endpoint="alert_archive")
api.add_org_resource(
    AlertFavoriteResource, "/api/alerts/<alert_id>/favorite", endpoint="alert_favorite"
)
api.add_org_resource(AlertEvaluateResource, "/api/alerts/<alert_id>/eval", endpoint="alert_eval")
api.add_org_resource(
    AlertSubscriptionListResource,
    "/api/alerts/<alert_id>/subscriptions",
    endpoint="alert_subscriptions",
)
api.add_org_resource(
    AlertSubscriptionResource,
    "/api/alerts/<alert_id>/subscriptions/<subscriber_id>",
    endpoint="alert_subscription",
)
api.add_org_resource(
    AlertEventListResource, "/api/alerts/<alert_id>/events", endpoint="alert_events"
)
api.add_org_resource(
    AlertEventResource,
    "/api/alerts/<alert_id>/events/<event_id>",
    endpoint="alert_event",
)
api.add_org_resource(AlertListResource, "/api/alerts", endpoint="alerts")
api.add_org_resource(AlertFavoriteListResource, "/api/alerts/favorites", endpoint="alert_favorites")
api.add_org_resource(AlertTagsResource, "/api/alerts/tags", endpoint="alerts_tags")
api.add_org_resource(MyAlertsResource, "/api/alerts/my", endpoint="my_alerts")
api.add_org_resource(AlertArchivedListResource, "/api/alerts/archive", endpoint="alerts_archive")
api.add_org_resource(MyAlertEventsResource, "/api/alert_events", endpoint="alert_events_feed")

api.add_org_resource(IndexerListResource, "/api/indexers", endpoint="indexers")
api.add_org_resource(IndexerResource, "/api/indexers/<indexer_id>", endpoint="indexer")
api.add_org_resource(
    IndexerArchiveResource,
    "/api/indexers/<indexer_id>/archive",
    endpoint="indexer_archive",
)
api.add_org_resource(
    IndexerArchivedListResource,
    "/api/indexers/archive",
    endpoint="indexers_archive",
)
api.add_org_resource(MyIndexersResource, "/api/indexers/my", endpoint="my_indexers")
api.add_org_resource(
    IndexerFavoriteResource,
    "/api/indexers/<indexer_id>/favorite",
    endpoint="indexer_favorite",
)
api.add_org_resource(
    IndexerFavoriteListResource,
    "/api/indexers/favorites",
    endpoint="indexer_favorites",
)
api.add_org_resource(IndexerTagsResource, "/api/indexers/tags", endpoint="indexers_tags")

# --- ML Models ---
api.add_org_resource(MLModelSearchResource, "/api/ml_models/search", endpoint="ml_models_search")
api.add_org_resource(MLModelRecentResource, "/api/ml_models/recent", endpoint="ml_models_recent")
api.add_org_resource(MLModelArchiveResource, "/api/ml_models/archive", endpoint="ml_models_archive")
api.add_org_resource(MyMLModelsResource, "/api/ml_models/my", endpoint="my_ml_models")
api.add_org_resource(MLModelFavoriteListResource, "/api/ml_models/favorites", endpoint="ml_model_favorites")
api.add_org_resource(MLModelTagsResource, "/api/ml_models/tags", endpoint="ml_models_tags")
api.add_org_resource(
    MLModelFavoriteResource,
    "/api/ml_models/<model_id>/favorite",
    endpoint="ml_model_favorite",
)
api.add_org_resource(MLModelTrainResource, "/api/ml_models/<model_id>/train", endpoint="ml_model_train")
api.add_org_resource(
    MLModelPredictResource, "/api/ml_models/<model_id>/predict", endpoint="ml_model_predict"
)
api.add_org_resource(MLModelStopResource, "/api/ml_models/<model_id>/stop", endpoint="ml_model_stop")
api.add_org_resource(
    MLModelStopPredictResource,
    "/api/ml_models/<model_id>/stop_predict",
    endpoint="ml_model_stop_predict",
)
api.add_org_resource(MLModelMuteResource, "/api/ml_models/<model_id>/mute", endpoint="ml_model_mute")
api.add_org_resource(MLModelCopyResource, "/api/ml_models/<model_id>/copy", endpoint="ml_model_copy")
api.add_org_resource(
    MLModelVersionRevertResource,
    "/api/ml_models/<model_id>/revert",
    endpoint="ml_model_revert",
)
api.add_org_resource(
    MLModelCreateFromVersionResource,
    "/api/ml_models/<model_id>/create_from_version",
    endpoint="ml_model_create_from_version",
)
api.add_org_resource(
    MLModelSubscriptionListResource,
    "/api/ml_models/<model_id>/subscriptions",
    endpoint="ml_model_subscriptions",
)
api.add_org_resource(
    MLModelSubscriptionResource,
    "/api/ml_models/<model_id>/subscriptions/<subscriber_id>",
    endpoint="ml_model_subscription",
)
api.add_org_resource(
    ModelVersionsResource,
    "/api/ml_models/<model_id>/versions",
    endpoint="ml_model_versions_for_model",
)
api.add_org_resource(
    ModelPredictionsResource,
    "/api/ml_models/<model_id>/predictions",
    endpoint="ml_model_predictions_for_model",
)
api.add_org_resource(MLModelResource, "/api/ml_models/<model_id>", endpoint="ml_model")
api.add_org_resource(MLModelListResource, "/api/ml_models", endpoint="ml_models")

# --- ML Model Versions ---
api.add_org_resource(
    MLModelVersionSearchResource, "/api/ml_models_versions/search", endpoint="ml_models_versions_search"
)
api.add_org_resource(
    MLModelVersionRecentResource, "/api/ml_models_versions/recent", endpoint="ml_models_versions_recent"
)
api.add_org_resource(
    MLModelVersionArchiveResource, "/api/ml_models_versions/archive", endpoint="ml_models_versions_archive"
)
api.add_org_resource(
    MyMLModelVersionsResource, "/api/ml_models_versions/my", endpoint="my_ml_models_versions"
)
api.add_org_resource(
    MLModelVersionFavoriteListResource,
    "/api/ml_models_versions/favorites",
    endpoint="ml_model_version_favorites",
)
api.add_org_resource(
    MLModelVersionTagsResource, "/api/ml_models_versions/tags", endpoint="ml_models_versions_tags"
)
api.add_org_resource(
    MLModelVersionFavoriteResource,
    "/api/ml_models_versions/<model_version_id>/favorite",
    endpoint="ml_model_version_favorite",
)
api.add_org_resource(
    MLModelVersionResource,
    "/api/ml_models_versions/<model_version_id>",
    endpoint="ml_model_version",
)
api.add_org_resource(
    MLModelVersionListResource, "/api/ml_models_versions", endpoint="ml_models_versions"
)

# --- Prediction Results ---
api.add_org_resource(
    PredictionResultSearchResource, "/api/predictions/search", endpoint="prediction_results_search"
)
api.add_org_resource(
    PredictionResultRecentResource, "/api/predictions/recent", endpoint="prediction_results_recent"
)
api.add_org_resource(
    PredictionResultArchiveResource, "/api/predictions/archive", endpoint="prediction_results_archive"
)
api.add_org_resource(
    MyPredictionResultsResource, "/api/predictions/my", endpoint="my_prediction_results"
)
api.add_org_resource(
    PredictionResultFavoriteListResource,
    "/api/predictions/favorites",
    endpoint="prediction_result_favorites",
)
api.add_org_resource(
    PredictionResultTagsResource, "/api/predictions/tags", endpoint="prediction_results_tags"
)
api.add_org_resource(
    PredictionResultFavoriteResource,
    "/api/predictions/<prediction_result_id>/favorite",
    endpoint="prediction_result_favorite",
)
api.add_org_resource(
    PredictionResultResource,
    "/api/predictions/<prediction_result_id>",
    endpoint="prediction_result",
)
api.add_org_resource(
    PredictionResultListResource, "/api/predictions", endpoint="prediction_results"
)

api.add_org_resource(DashboardListResource, "/api/dashboards", endpoint="dashboards")
api.add_org_resource(DashboardResource, "/api/dashboards/<dashboard_id>", endpoint="dashboard")
api.add_org_resource(
    PublicDashboardResource,
    "/api/dashboards/public/<token>",
    endpoint="public_dashboard",
)
api.add_org_resource(
    DashboardShareResource,
    "/api/dashboards/<dashboard_id>/share",
    endpoint="dashboard_share",
)

api.add_org_resource(DataSourceTypeListResource, "/api/data_sources/types", endpoint="data_source_types")
api.add_org_resource(DataSourceListResource, "/api/data_sources", endpoint="data_sources")
api.add_org_resource(DataSourceSchemaResource, "/api/data_sources/<data_source_id>/schema")
api.add_org_resource(DatabricksDatabaseListResource, "/api/databricks/databases/<data_source_id>")
api.add_org_resource(
    DatabricksSchemaResource,
    "/api/databricks/databases/<data_source_id>/<database_name>/tables",
)
api.add_org_resource(
    DatabricksTableColumnListResource,
    "/api/databricks/databases/<data_source_id>/<database_name>/columns/<table_name>",
)
api.add_org_resource(DataSourcePauseResource, "/api/data_sources/<data_source_id>/pause")
api.add_org_resource(DataSourceTestResource, "/api/data_sources/<data_source_id>/test")
api.add_org_resource(DataSourceResource, "/api/data_sources/<data_source_id>", endpoint="data_source")

api.add_org_resource(GroupListResource, "/api/groups", endpoint="groups")
api.add_org_resource(GroupResource, "/api/groups/<group_id>", endpoint="group")
api.add_org_resource(GroupMemberListResource, "/api/groups/<group_id>/members", endpoint="group_members")
api.add_org_resource(
    GroupMemberResource,
    "/api/groups/<group_id>/members/<user_id>",
    endpoint="group_member",
)
api.add_org_resource(
    GroupDataSourceListResource,
    "/api/groups/<group_id>/data_sources",
    endpoint="group_data_sources",
)
api.add_org_resource(
    GroupDataSourceResource,
    "/api/groups/<group_id>/data_sources/<data_source_id>",
    endpoint="group_data_source",
)

api.add_org_resource(EventsResource, "/api/events", endpoint="events")

api.add_org_resource(QueryFavoriteListResource, "/api/queries/favorites", endpoint="query_favorites")
api.add_org_resource(QueryFavoriteResource, "/api/queries/<query_id>/favorite", endpoint="query_favorite")
api.add_org_resource(
    DashboardFavoriteListResource,
    "/api/dashboards/favorites",
    endpoint="dashboard_favorites",
)
api.add_org_resource(
    DashboardFavoriteResource,
    "/api/dashboards/<object_id>/favorite",
    endpoint="dashboard_favorite",
)
api.add_org_resource(DashboardForkResource, "/api/dashboards/<dashboard_id>/fork", endpoint="dashboard_fork")

api.add_org_resource(MyDashboardsResource, "/api/dashboards/my", endpoint="my_dashboards")

api.add_org_resource(QueryTagsResource, "/api/queries/tags", endpoint="query_tags")
api.add_org_resource(DashboardTagsResource, "/api/dashboards/tags", endpoint="dashboard_tags")

api.add_org_resource(QuerySearchResource, "/api/queries/search", endpoint="queries_search")
api.add_org_resource(QueryRecentResource, "/api/queries/recent", endpoint="recent_queries")
api.add_org_resource(QueryArchiveResource, "/api/queries/archive", endpoint="queries_archive")
api.add_org_resource(QueryListResource, "/api/queries", endpoint="queries")
api.add_org_resource(MyQueriesResource, "/api/queries/my", endpoint="my_queries")
api.add_org_resource(QueryRefreshResource, "/api/queries/<query_id>/refresh", endpoint="query_refresh")
api.add_org_resource(QueryResource, "/api/queries/<query_id>", endpoint="query")
api.add_org_resource(QueryForkResource, "/api/queries/<query_id>/fork", endpoint="query_fork")
api.add_org_resource(
    QueryRegenerateApiKeyResource,
    "/api/queries/<query_id>/regenerate_api_key",
    endpoint="query_regenerate_api_key",
)

api.add_org_resource(
    ObjectPermissionsListResource,
    "/api/<object_type>/<object_id>/acl",
    endpoint="object_permissions",
)
api.add_org_resource(
    CheckPermissionResource,
    "/api/<object_type>/<object_id>/acl/<access_type>",
    endpoint="check_permissions",
)

api.add_org_resource(QueryResultListResource, "/api/query_results", endpoint="query_results")
api.add_org_resource(
    QueryResultDropdownResource,
    "/api/queries/<query_id>/dropdown",
    endpoint="query_result_dropdown",
)
api.add_org_resource(
    QueryDropdownsResource,
    "/api/queries/<query_id>/dropdowns/<dropdown_query_id>",
    endpoint="query_result_dropdowns",
)
api.add_org_resource(
    QueryResultResource,
    "/api/query_results/<query_result_id>.<filetype>",
    "/api/query_results/<query_result_id>",
    "/api/queries/<query_id>/results",
    "/api/queries/<query_id>/results.<filetype>",
    "/api/queries/<query_id>/results/<query_result_id>.<filetype>",
    endpoint="query_result",
)
api.add_org_resource(
    JobResource,
    "/api/jobs/<job_id>",
    "/api/queries/<query_id>/jobs/<job_id>",
    endpoint="job",
)

api.add_org_resource(UserListResource, "/api/users", endpoint="users")
api.add_org_resource(UserResource, "/api/users/<user_id>", endpoint="user")
api.add_org_resource(UserInviteResource, "/api/users/<user_id>/invite", endpoint="user_invite")
api.add_org_resource(
    UserResetPasswordResource,
    "/api/users/<user_id>/reset_password",
    endpoint="user_reset_password",
)
api.add_org_resource(
    UserRegenerateApiKeyResource,
    "/api/users/<user_id>/regenerate_api_key",
    endpoint="user_regenerate_api_key",
)
api.add_org_resource(UserDisableResource, "/api/users/<user_id>/disable", endpoint="user_disable")

api.add_org_resource(VisualizationListResource, "/api/visualizations", endpoint="visualizations")
api.add_org_resource(
    VisualizationResource,
    "/api/visualizations/<visualization_id>",
    endpoint="visualization",
)

api.add_org_resource(WidgetListResource, "/api/widgets", endpoint="widgets")
api.add_org_resource(WidgetResource, "/api/widgets/<int:widget_id>", endpoint="widget")

api.add_org_resource(DestinationTypeListResource, "/api/destinations/types", endpoint="destination_types")
api.add_org_resource(MyDestinationsResource, "/api/destinations/my", endpoint="my_destinations")
api.add_org_resource(
    DestinationFavoriteListResource, "/api/destinations/favorites", endpoint="destination_favorites"
)
api.add_org_resource(
    DestinationArchivedListResource, "/api/destinations/archive", endpoint="destinations_archived"
)
api.add_org_resource(DestinationTagsResource, "/api/destinations/tags", endpoint="destination_tags")
api.add_org_resource(
    DestinationArchiveResource,
    "/api/destinations/<destination_id>/archive",
    endpoint="destination_archive",
)
api.add_org_resource(
    DestinationFavoriteResource,
    "/api/destinations/<destination_id>/favorite",
    endpoint="destination_favorite",
)
api.add_org_resource(DestinationResource, "/api/destinations/<destination_id>", endpoint="destination")
api.add_org_resource(DestinationListResource, "/api/destinations", endpoint="destinations")

api.add_org_resource(MyQuerySnippetsResource, "/api/query_snippets/my", endpoint="my_query_snippets")
api.add_org_resource(
    QuerySnippetFavoriteListResource, "/api/query_snippets/favorites", endpoint="query_snippet_favorites"
)
api.add_org_resource(
    QuerySnippetArchivedListResource, "/api/query_snippets/archive", endpoint="query_snippets_archived"
)
api.add_org_resource(QuerySnippetTagsResource, "/api/query_snippets/tags", endpoint="query_snippet_tags")
api.add_org_resource(
    QuerySnippetArchiveResource,
    "/api/query_snippets/<snippet_id>/archive",
    endpoint="query_snippet_archive",
)
api.add_org_resource(
    QuerySnippetFavoriteResource,
    "/api/query_snippets/<snippet_id>/favorite",
    endpoint="query_snippet_favorite",
)
api.add_org_resource(QuerySnippetResource, "/api/query_snippets/<snippet_id>", endpoint="query_snippet")
api.add_org_resource(QuerySnippetListResource, "/api/query_snippets", endpoint="query_snippets")

api.add_org_resource(OrganizationSettings, "/api/settings/organization", endpoint="organization_settings")

api.add_org_resource(AssistantStatusResource, "/api/assistant/status", endpoint="assistant_status")
api.add_org_resource(AssistantThreadListResource, "/api/assistant/threads", endpoint="assistant_threads")
api.add_org_resource(
    AssistantThreadMessagesResource,
    "/api/assistant/threads/<thread_id>/messages",
    endpoint="assistant_thread_messages",
)
api.add_org_resource(
    AssistantThreadResource,
    "/api/assistant/threads/<thread_id>",
    endpoint="assistant_thread",
)
api.add_org_resource(AssistantChatResource, "/api/assistant/chat", endpoint="assistant_chat")
api.add_org_resource(
    AssistantGenerateQueryResource,
    "/api/assistant/generate-query",
    endpoint="assistant_generate_query",
)
api.add_org_resource(
    AssistantChatStreamResource,
    "/api/assistant/chat/stream",
    endpoint="assistant_chat_stream",
)
api.add_org_resource(
    AssistantVisualizationPreviewResource,
    "/api/assistant/previews/visualizations/<int:visualization_id>",
    endpoint="assistant_preview_visualization",
)
api.add_org_resource(
    AssistantQueryPreviewResource,
    "/api/assistant/previews/queries/<int:query_id>",
    endpoint="assistant_preview_query",
)
api.add_org_resource(
    AssistantDashboardPreviewResource,
    "/api/assistant/previews/dashboards/<int:dashboard_id>",
    endpoint="assistant_preview_dashboard",
)
