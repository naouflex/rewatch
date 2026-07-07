import PropTypes from "prop-types";
import React from "react";
import { getDataSourceIconUrl } from "@/services/data-source";

export function QuerySourceTypeIcon({ dataSource, type, alt, ...props }) {
  const src = dataSource ? getDataSourceIconUrl(dataSource) : getDataSourceIconUrl({ type });
  return <img src={src} width="20" alt={alt} {...props} />;
}

QuerySourceTypeIcon.propTypes = {
  dataSource: PropTypes.shape({
    type: PropTypes.string.isRequired,
    icon_url: PropTypes.string,
  }),
  type: PropTypes.string,
  alt: PropTypes.string,
};
