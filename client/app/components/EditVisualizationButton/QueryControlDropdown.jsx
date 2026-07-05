import React, { useMemo } from "react";
import PropTypes from "prop-types";
import Dropdown from "antd/lib/dropdown";
import Button from "antd/lib/button";
import PlainButton from "@/components/PlainButton";
import { clientConfig } from "@/services/auth";

import PlusCircleFilledIcon from "@ant-design/icons/PlusCircleFilled";
import ShareAltOutlinedIcon from "@ant-design/icons/ShareAltOutlined";
import FileOutlinedIcon from "@ant-design/icons/FileOutlined";
import FileExcelOutlinedIcon from "@ant-design/icons/FileExcelOutlined";
import EllipsisOutlinedIcon from "@ant-design/icons/EllipsisOutlined";

import QueryResultsLink from "./QueryResultsLink";

export default function QueryControlDropdown(props) {
  const menuItems = useMemo(() => {
    const items = [];

    if (!props.query.isNew() && (!props.query.is_draft || !props.query.is_archived)) {
      items.push({
        key: "add-to-dashboard",
        label: (
          <PlainButton onClick={() => props.openAddToDashboardForm(props.selectedTab)}>
            <PlusCircleFilledIcon /> Add to Dashboard
          </PlainButton>
        ),
      });
    }
    if (!clientConfig.disablePublicUrls && !props.query.isNew()) {
      items.push({
        key: "embed",
        label: (
          <PlainButton
            onClick={() => props.showEmbedDialog(props.query, props.selectedTab)}
            data-test="ShowEmbedDialogButton">
            <ShareAltOutlinedIcon /> Embed Elsewhere
          </PlainButton>
        ),
      });
    }

    const downloadDisabled = props.queryExecuting || !props.queryResult.getData || !props.queryResult.getData();
    items.push({
      key: "download-csv",
      label: (
        <QueryResultsLink
          fileType="csv"
          disabled={downloadDisabled}
          query={props.query}
          queryResult={props.queryResult}
          embed={props.embed}
          apiKey={props.apiKey}>
          <FileOutlinedIcon /> Download as CSV File
        </QueryResultsLink>
      ),
    });
    items.push({
      key: "download-tsv",
      label: (
        <QueryResultsLink
          fileType="tsv"
          disabled={downloadDisabled}
          query={props.query}
          queryResult={props.queryResult}
          embed={props.embed}
          apiKey={props.apiKey}>
          <FileOutlinedIcon /> Download as TSV File
        </QueryResultsLink>
      ),
    });
    items.push({
      key: "download-excel",
      label: (
        <QueryResultsLink
          fileType="xlsx"
          disabled={downloadDisabled}
          query={props.query}
          queryResult={props.queryResult}
          embed={props.embed}
          apiKey={props.apiKey}>
          <FileExcelOutlinedIcon /> Download as Excel File
        </QueryResultsLink>
      ),
    });

    return items;
  }, [props]);

  return (
    <Dropdown
      trigger={["click"]}
      menu={{ items: menuItems }}
      classNames={{ root: "query-control-dropdown-overlay" }}>
      <Button data-test="QueryControlDropdownButton">
        <EllipsisOutlinedIcon rotate={90} />
      </Button>
    </Dropdown>
  );
}

QueryControlDropdown.propTypes = {
  query: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
  queryResult: PropTypes.object, // eslint-disable-line react/forbid-prop-types
  queryExecuting: PropTypes.bool.isRequired,
  showEmbedDialog: PropTypes.func.isRequired,
  embed: PropTypes.bool,
  apiKey: PropTypes.string,
  selectedTab: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  openAddToDashboardForm: PropTypes.func.isRequired,
};

QueryControlDropdown.defaultProps = {
  queryResult: {},
  embed: false,
  apiKey: "",
  selectedTab: "",
};
