import React, { useState, useCallback, useMemo } from "react";
import PropTypes from "prop-types";
import cx from "classnames";

import Modal from "antd/lib/modal";
import Dropdown from "antd/lib/dropdown";
import Button from "antd/lib/button";
import Select from "antd/lib/select";
import notification from "antd/lib/notification";

import LoadingOutlinedIcon from "@ant-design/icons/LoadingOutlined";
import EllipsisOutlinedIcon from "@ant-design/icons/EllipsisOutlined";
import PlainButton from "@/components/PlainButton";

import MLModel from "@/services/ml-model";
import "./MenuButton.less";

export default function MenuButton({
  doDelete,
  canEdit,
  mute,
  unmute,
  muted,
  doArchive,
  doUnarchive,
  archived,
  trainModel,
  stopTraining,
  stopPredicting,
  predict,
  modelId,
  revertToVersion,
  createFromVersion,
  copyModel,
  stateTrain,
  statePredict,
}) {

  const [loading, setLoading] = useState(false);
  const [availableVersions, setAvailableVersions] = useState([]);
  const [selectedVersion, setSelectedVersion] = useState(null);
  const [isRevertModalVisible, setIsRevertModalVisible] = useState(false);
  const [isCreateModalVisible, setIsCreateModalVisible] = useState(false);
  const [isCopyModalVisible, setIsCopyModalVisible] = useState(false);

  const execute = useCallback(action => {
    setLoading(true);
    return action().finally(() => {
      setLoading(false);
    });
  }, []);

  const confirmDelete = useCallback(() => {
    Modal.confirm({
      title: "Delete Model",
      content: "Are you sure you want to delete this model?",
      okText: "Delete",
      okType: "danger",
      onOk: () => execute(doDelete),
      maskClosable: true,
      autoFocusButton: null,
      
    });
  }, [doDelete, execute]);

  const confirmArchive = useCallback(() => {
    Modal.confirm({
      title: "Archive Model",
      content: "Are you sure you want to archive this model?",
      okText: "Archive",
      okType: "danger",
      onOk: () => execute(doArchive),
      maskClosable: true,
      autoFocusButton: null,
    });
  }, [doArchive, execute]);

  const confirmUnarchive = useCallback(() => {
    Modal.confirm({
      title: "Unarchive Model",
      content: "Are you sure you want to unarchive this model?",
      okText: "Unarchive",
      okType: "danger",
      onOk: () => execute(doUnarchive),
      maskClosable: true,
      autoFocusButton: null,
    });
  }, [doUnarchive, execute]);

  const showRevertModal = useCallback(async () => {
    setLoading(true);
    setSelectedVersion(null);
    try {
      const model = await MLModel.get({ id: modelId });
      const versions = await MLModel.getVersions(modelId);
      const availableVersions = versions.filter(v => v.version !== model.version);
      setAvailableVersions(availableVersions);
      setIsRevertModalVisible(true);
    } catch (error) {
      console.error("Error fetching versions:", error);
      notification.error({
        message: "Failed to fetch available versions",
        description: error instanceof Error ? error.message : "An unknown error occurred",
      });
    } finally {
      setLoading(false);
    }
  }, [modelId]);

  const handleRevertOk = useCallback(() => {
    if (!selectedVersion) {
      notification.warning({ message: "Please select a version to revert to" });
      return;
    }
    execute(() => revertToVersion(selectedVersion)).then(() => {
      setSelectedVersion(null);
      setIsRevertModalVisible(false);
    });
  }, [selectedVersion, execute, revertToVersion]);

  const handleRevertCancel = useCallback(() => {
    setSelectedVersion(null);
    setIsRevertModalVisible(false);
  }, []);

  const handleStopTraining = useCallback(() => {
    execute(() => MLModel.stopTraining(modelId)).then(() => {
      notification.success({ message: "Training stopped successfully" });
      // Add a refresh here
      window.location.reload();
    }).catch(error => {
      notification.error({ message: "Failed to stop training", description: error.message });
    });
  }, [modelId, execute]);

  const handleStopPrediction = useCallback(() => {
    execute(() => MLModel.stopPredicting(modelId)).then(() => {
      notification.success({ message: "Prediction stopped successfully" });
      // Add a refresh here as well
      window.location.reload();
    }).catch(error => {
      notification.error({ message: "Failed to stop prediction", description: error.message });
    });
  }, [modelId, execute]);

  const showCreateModal = useCallback(async () => {
    setLoading(true);
    setSelectedVersion(null);
    try {
      const model = await MLModel.get({ id: modelId });
      const versions = await MLModel.getVersions(modelId);
      const availableVersions = versions.filter(v => v.version !== model.version);
      setAvailableVersions(availableVersions);
      setIsCreateModalVisible(true);
    } catch (error) {
      console.error("Error fetching versions:", error);
      notification.error({
        message: "Failed to fetch available versions",
        description: error instanceof Error ? error.message : "An unknown error occurred",
      });
    } finally {
      setLoading(false);
    }
  }, [modelId]);

  const handleCreateOk = useCallback(() => {
    if (!selectedVersion) {
      notification.warning({ message: "Please select a version to create from" });
      return;
    }
    execute(() => createFromVersion(selectedVersion)).then(() => {
      setSelectedVersion(null);
      setIsCreateModalVisible(false);
    });
  }, [selectedVersion, execute, createFromVersion]);

  const showCopyModal = useCallback(() => {
    setIsCopyModalVisible(true);
  }, []);

  const handleCopyOk = useCallback(() => {
    execute(() => copyModel()).then(() => {
      setIsCopyModalVisible(false);
    });
  }, [execute, copyModel]);

  const handleCreateCancel = useCallback(() => {
    setSelectedVersion(null);
    setIsCreateModalVisible(false);
  }, []);

  const handleCopyCancel = useCallback(() => {
    setIsCopyModalVisible(false);
  }, []);

  const isTraining = stateTrain === 'training';
  const isPredicting = statePredict === 'predicting';
  const canTrain = stateTrain !== 'training';
  const canPredict = statePredict !== 'predicting' && stateTrain !== 'training';

  const menuItems = useMemo(() => {
    const items = [
      {
        key: "mute",
        label: muted ? (
          <PlainButton onClick={() => execute(unmute)}>Unmute Notifications</PlainButton>
        ) : (
          <PlainButton onClick={() => execute(mute)}>Mute Notifications</PlainButton>
        ),
      },
      {
        key: "delete",
        label: <PlainButton onClick={confirmDelete}>Delete</PlainButton>,
      },
      {
        key: "archive",
        label: archived ? (
          <PlainButton onClick={confirmUnarchive}>Unarchive</PlainButton>
        ) : (
          <PlainButton onClick={confirmArchive}>Archive</PlainButton>
        ),
      },
    ];

    if (canTrain) {
      items.push({
        key: "train",
        label: <PlainButton onClick={() => execute(trainModel)}>Train Model</PlainButton>,
      });
    }
    if (isTraining) {
      items.push({
        key: "stop-training",
        label: <PlainButton onClick={handleStopTraining}>Stop Training</PlainButton>,
      });
    }
    if (canPredict) {
      items.push({
        key: "predict",
        label: <PlainButton onClick={() => execute(predict)}>Predict</PlainButton>,
      });
    }
    if (isPredicting) {
      items.push({
        key: "stop-prediction",
        label: <PlainButton onClick={handleStopPrediction}>Stop Prediction</PlainButton>,
      });
    }

    items.push(
      {
        key: "revert",
        label: <PlainButton onClick={showRevertModal}>Revert to Version</PlainButton>,
      },
      {
        key: "create-from-version",
        label: <PlainButton onClick={showCreateModal}>Create from Version</PlainButton>,
      },
      {
        key: "copy",
        label: <PlainButton onClick={showCopyModal}>Copy Model</PlainButton>,
      }
    );

    return items;
  }, [
    archived,
    canPredict,
    canTrain,
    confirmArchive,
    confirmDelete,
    confirmUnarchive,
    execute,
    handleStopPrediction,
    handleStopTraining,
    isPredicting,
    isTraining,
    mute,
    muted,
    predict,
    showCopyModal,
    showCreateModal,
    showRevertModal,
    trainModel,
    unmute,
  ]);

  return (
    <>
      <Dropdown
        className={cx("m-l-5", { disabled: !canEdit })}
        trigger={[canEdit ? "click" : undefined]}
        placement="bottomRight"
        menu={{ items: menuItems }}>
        <Button aria-label="More actions">
          {loading ? <LoadingOutlinedIcon /> : <EllipsisOutlinedIcon rotate={90} aria-hidden="true" />}
        </Button>
      </Dropdown>

      <Modal
        title="Revert Model Version"
        open={isRevertModalVisible}
        onOk={handleRevertOk}
        onCancel={handleRevertCancel}
      >
        <Select
          style={{ width: '100%' }}
          placeholder="Select a version"
          onChange={(value) => {
            setSelectedVersion(value); // Update state correctly
          }}
          value={selectedVersion} // Ensure value is bound to state
        >
          {availableVersions.map((version) => (
            <Select.Option 
              key={`${version.id || version.version}`} 
              value={version.version}
            >
              {version.name} v{version.version}
            </Select.Option>
          ))}
        </Select>
      </Modal>

      <Modal
        title="Create Model from Version"
        open={isCreateModalVisible}
        onOk={handleCreateOk}
        onCancel={handleCreateCancel}
      >
        <Select
          style={{ width: '100%' }}
          placeholder="Select a version"
          onChange={(value) => {
            setSelectedVersion(value);
          }}
          value={selectedVersion}
        >
          {availableVersions.map((version) => (
            <Select.Option 
              key={`${version.id || version.version}`} 
              value={version.version}
            >
              {version.name} v{version.version}
            </Select.Option>
          ))}
        </Select>
      </Modal>

      <Modal
        title="Copy Model"
        open={isCopyModalVisible}
        onOk={handleCopyOk}
        onCancel={handleCopyCancel}
      >
        <p>Are you sure you want to create a copy of this model?</p>
      </Modal>
    </>
  );
}

MenuButton.propTypes = {
  doDelete: PropTypes.func.isRequired,
  doArchive: PropTypes.func.isRequired,
  doUnarchive: PropTypes.func.isRequired,
  canEdit: PropTypes.bool.isRequired,
  mute: PropTypes.func.isRequired,
  unmute: PropTypes.func.isRequired,
  muted: PropTypes.bool,
  archived: PropTypes.bool.isRequired,
  trainModel: PropTypes.func.isRequired,
  stopTraining: PropTypes.func.isRequired,
  stopPredicting: PropTypes.func.isRequired,
  predict: PropTypes.func.isRequired,
  modelId: PropTypes.number.isRequired,
  revertToVersion: PropTypes.func.isRequired,
  createFromVersion: PropTypes.func.isRequired,
  stateTrain: PropTypes.oneOf(['training', 'trained', 'untrained']).isRequired,
  statePredict: PropTypes.oneOf(['predicting', 'predicted', 'unpredicted']).isRequired,
};

MenuButton.defaultProps = {
  muted: false,
};
