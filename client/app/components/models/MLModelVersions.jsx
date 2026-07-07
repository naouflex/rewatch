import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import TimeAgo from "@/components/TimeAgo";
import Paginator from "@/components/Paginator";
import Tooltip from "@/components/Tooltip";
import ItemsTable, { Columns } from "@/components/items-list/components/ItemsTable";
import LoadingState from "@/components/items-list/components/LoadingState";
import * as Grid from "antd/lib/grid";
import JsonViewInteractive from "@/components/json-view-interactive/JsonViewInteractive";
import Button from "antd/lib/button";
import ModelVersionPickModal from "./ModelVersionPickModal";
import { useTheme } from "@/components/ThemeProvider";
import "./MLModelVersions.less";

// Add this helper function at the top of the file, after the imports
const formatDate = (date) => {
  if (!date) return 'N/A';
  return new Intl.DateTimeFormat('en-GB', {
    year: '2-digit', 
    month: '2-digit', 
    day: '2-digit', 
    hour: '2-digit', 
    minute: '2-digit'
  }).format(new Date(date)).replace(/,/g, '');
};

// Move showRevertModal outside of the component and make it a regular function
function showRevertModal(version, setSelectedVersion, setIsRevertModalVisible) {
  setSelectedVersion(version);
  setIsRevertModalVisible(true);
}

const columns = [
  Columns.custom.sortable(
    (text, version) => version.version,
    { title: "Version", field: "version", width: "10%" }
  ),
  Columns.custom.sortable(
    (text, version) => (
      <div>
        <Tooltip title={<div align="center">{formatDate(version.created_at)}<br/><TimeAgo date={version.created_at} /></div>}>
          {formatDate(version.created_at)}
        </Tooltip>
      </div>
    ),
    {
      title: "Date", 
      field: "created_at", 
      width: "10%" 
    }
  ),
  Columns.custom.sortable(
    (text, version) => version.user.name,
    { title: "Created By", field: "user.name", width: "15%" }
  ),
  Columns.custom.sortable(
    (text, version) => version.name,
    { title: "Name", field: "name", width: "15%" }
  ),
  Columns.custom.sortable(
    (text, version) => version.description,
    { title: "Description", field: "description", width: "20%" }
  ),
  Columns.custom.sortable(
    (text, version) => version.changes,
    { title: "Changes", field: "changes", width: "15%" }
  ),
  Columns.custom.sortable(
    (text, version) => (
      <div className="json-cell">
        <JsonViewInteractive value={version.options} />
      </div>
    ),
    { title: "Options", field: "options", width: "20%" }
  ),
  Columns.custom.sortable(
    (text, version) => (
      <div className="json-cell">
        <JsonViewInteractive value={version.metrics} />
      </div>
    ),
    { title: "Metrics", field: "metrics", width: "20%" }
  ),
  Columns.custom.sortable(
    (text, version) => version.state,
    { title: "State", field: "state", width: "10%" }
  ),
  Columns.custom(
    (text, version, { setSelectedVersion, setIsRevertModalVisible }) => (
      <Button 
        type="primary" 
        size="small" 
        onClick={() => showRevertModal(version, setSelectedVersion, setIsRevertModalVisible)}
      >
        Revert
      </Button>
    ),
    { title: "Revert", width: "10%" }
  ),
  Columns.custom(
    (text, version) => (
      <Button size="small" onClick={() => window.location.href = `/ml_models_versions/${version.id}`}>
        Go to Version
      </Button>
    ),
    { title: "Details", width: "10%" }
  ),
];

function MLModelVersions({ versions, revertToVersion }) {
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [loading, setLoading] = useState(true);
  const [sortedVersions, setSortedVersions] = useState([]);
  const [orderByField, setOrderByField] = useState(null);
  const [orderByReverse, setOrderByReverse] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [isRevertModalVisible, setIsRevertModalVisible] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState(null);
  const { isDarkMode } = useTheme();

  useEffect(() => {
    if (versions === null || versions === undefined) {
      setLoading(true);
      setSortedVersions([]);
    } else if (versions.length === 0) {
      setLoading(false);
      setSortedVersions([]);
    } else {
      setSortedVersions(versions.map(v => ({ 
        ...v, 
        revertToVersion,
        setSelectedVersion,
        setIsRevertModalVisible
      })));
      setLoading(false);
    }
  }, [versions, revertToVersion]);

  const toggleSorting = (field) => {
    const isReverse = orderByField === field ? !orderByReverse : false;
    setOrderByField(field);
    setOrderByReverse(isReverse);

    const sorted = [...sortedVersions].sort((a, b) => {
      const getValue = (obj, path) => path.split('.').reduce((o, p) => (o ? o[p] : undefined), obj);

      const aValue = getValue(a, field);
      const bValue = getValue(b, field);

      const isDateField = field === 'created_at';
      const aValueProcessed = isDateField ? new Date(aValue) : aValue;
      const bValueProcessed = isDateField ? new Date(bValue) : bValue;

      if (aValueProcessed < bValueProcessed) return isReverse ? 1 : -1;
      if (aValueProcessed > bValueProcessed) return isReverse ? -1 : 1;
      return 0;
    });

    setSortedVersions(sorted);
  };

  const filteredVersions = sortedVersions.filter(version =>
    Object.values(version).some(value => {
      const stringValue = value !== null && value !== undefined ? String(value) : "";
      return stringValue.toLowerCase().includes(searchTerm.toLowerCase());
    })
  );
  const currentItems = filteredVersions.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const handleRevertOk = () => {
    if (selectedVersion) {
      revertToVersion(selectedVersion.version);
      setIsRevertModalVisible(false);
    }
  };

  const handleRevertCancel = () => {
    setIsRevertModalVisible(false);
  };

  const columnsWithActions = [
    ...columns.slice(0, -2),
    Columns.custom(
      (text, version) => (
        <Button 
          type="primary" 
          size="small" 
          onClick={() => showRevertModal(version, setSelectedVersion, setIsRevertModalVisible)}
        >
          Revert
        </Button>
      ),
      { title: "Revert", width: "10%" }
    ),
    Columns.custom(
      (text, version) => (
        <Button size="small" onClick={() => window.location.href = `/ml_models_versions/${version.id}`}>
          Go to Version
        </Button>
      ),
      { title: "Details", width: "10%" }
    ),
  ];

  return (
    <div className={`model-versions ${isDarkMode ? 'dark-mode' : ''}`}>
      <h3 className={`model-versions-title ${isDarkMode ? 'dark-mode' : ''}`}>Model Versions</h3>
      {loading ? (
        <LoadingState />
      ) : sortedVersions.length === 0 ? (
        <div className="text-center">No versions available.</div>
      ) : (
        <div className={`bg-white tiled p-20 ${isDarkMode ? 'dark-mode' : ''}`}>
          <input
            type="text"
            placeholder="Search..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className={`search-input ${isDarkMode ? 'dark-mode' : ''}`}
            style={{ marginBottom: "20px", padding: "10px", width: "100%", borderRadius: "2px" }}
          />
          <Grid.Row gutter={16}>
            <Grid.Col xs={24}>
              <div className={`bg-white tiled table-responsive ${isDarkMode ? 'dark-mode' : ''}`}>
                <ItemsTable
                  items={currentItems}
                  columns={columnsWithActions}
                  loading={loading}
                  orderByField={orderByField}
                  orderByReverse={orderByReverse}
                  toggleSorting={toggleSorting}
                  sortColumn={orderByField}
                  sortOrder={orderByReverse ? 'descend' : 'ascend'}
                  className={isDarkMode ? 'dark-mode' : ''}
                />
                <Paginator
                  showPageSizeSelect
                  totalCount={filteredVersions.length}
                  pageSize={pageSize}
                  onPageSizeChange={setPageSize}
                  page={currentPage}
                  onChange={setCurrentPage}
                  className={isDarkMode ? 'dark-mode' : ''}
                />
              </div>
            </Grid.Col>
          </Grid.Row>
        </div>
      )}
      <ModelVersionPickModal
        open={isRevertModalVisible}
        title="Revert Model Version"
        description="This action cannot be undone."
        okText="Revert"
        onOk={handleRevertOk}
        onCancel={handleRevertCancel}>
        <p>Are you sure you want to revert to version {selectedVersion?.version}?</p>
      </ModelVersionPickModal>
    </div>
  );
}

MLModelVersions.propTypes = {
  versions: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      model_id: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      description: PropTypes.string,
      version: PropTypes.number.isRequired,
      created_at: PropTypes.string.isRequired,
      updated_at: PropTypes.string.isRequired,
      user: PropTypes.shape({
        id: PropTypes.string.isRequired,
        name: PropTypes.string.isRequired,
      }),
      changes: PropTypes.string,
      metrics: PropTypes.object,
      options: PropTypes.object.isRequired,
      state: PropTypes.string.isRequired,
      state_train: PropTypes.string.isRequired,
      state_predict: PropTypes.string.isRequired,
    })
  ).isRequired,
  revertToVersion: PropTypes.func.isRequired,
};

MLModelVersions.defaultProps = {
  versions: [],
};

export default MLModelVersions;
