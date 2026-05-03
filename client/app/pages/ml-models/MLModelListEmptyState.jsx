import React from "react";
import PropTypes from "prop-types";
import Link from "@/components/Link";
import BigMessage from "@/components/BigMessage";
import NoTaggedObjectsFound from "@/components/NoTaggedObjectsFound";
import EmptyState, { EmptyStateHelpMessage } from "@/components/empty-state/EmptyState";
import DynamicComponent from "@/components/DynamicComponent";
import { currentUser } from "@/services/auth";
import HelpTrigger from "@/components/HelpTrigger";

export default function ModelListEmptyState({ page, searchTerm, selectedTags }) {
  if (searchTerm !== "") {
    return <BigMessage message="Sorry, we couldn't find anything." icon="fa-search" />;
  }

  if (selectedTags.length > 0) {
    return <NoTaggedObjectsFound objectType="ml_models" tags={selectedTags} />;
  }

  switch (page) {
    case "favorites":
      return <BigMessage message="Mark models as Favorite to list them here." icon="fa-star" />;
    case "archive":
      return <BigMessage message="Archived models will be listed here." icon="fa-archive" />;
    case "my":
      const myMessage = currentUser.hasPermission("create_model") ? (
        <span>
          <Link.Button href="ml_models/new" type="primary" size="small">
            Create your first model !
          </Link.Button>{" "}
          <HelpTrigger className="f-13" type="MODELS" showTooltip={false}>
            Need help?
          </HelpTrigger>
        </span>
      ) : (
        <span>Sorry, we couldn't find anything.</span>
      );
      return <BigMessage icon="fa-search">{myMessage}</BigMessage>;
    default:
      return (
        <DynamicComponent name="MLMLModelsList.EmptyState">
          <EmptyState
            icon="fa fa-cogs"
            illustration="query"
            description="Building and managing your models."
            helpMessage={<EmptyStateHelpMessage helpTriggerType="MODELS" />}
          />
        </DynamicComponent>
      );
  }
}

ModelListEmptyState.propTypes = {
  page: PropTypes.string.isRequired,
  searchTerm: PropTypes.string.isRequired,
  selectedTags: PropTypes.array.isRequired, // eslint-disable-line react/forbid-prop-types
};
