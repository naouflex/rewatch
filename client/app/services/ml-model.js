import { axios } from "@/services/axios";
import { extend, has, merge } from "lodash";
import { currentUser } from "@/services/auth";

const normalizeCondition = {
  "greater than": ">",
  "less than": "<",
  equals: "=",
};

const transformResponse = data =>
  merge({}, data, {
    options: {
      op_train: normalizeCondition[data.options.op_train] || data.options.op_train,
      op_predict: normalizeCondition[data.options.op_predict] || data.options.op_predict,
      regressor: data.options.regressor || "RandomForest",
      train_size: data.options.train_size || 0.75,
      test_size: data.options.test_size || 0.25,
      random_state: data.options.random_state || 42,
      features: data.options.features || [],
      targets: data.options.targets || [],
      categories: data.options.categories || [],
      timestamp: data.options.timestamp || null,
      rearm_train: data.options.rearm_train || "never",
      rearm_predict: data.options.rearm_predict || "never",
    },
    query: data.query || {},
    destinations: data.destinations || [],
    tags: data.tags || [],
    user: data.user || currentUser,
    version: data.version || 1,
    name: data.name || "New MLModel",
    description: data.description || "This model is awesome!",
    state: data.state || "unknown",
    state_train: data.state_train || "unknown",
    state_predict: data.state_predict || "unknown",
  });

const transformRequest = data => {
  const newData = Object.assign({}, data);
  if (newData.query_id === undefined) {
    newData.query_id = newData.query && newData.query.id;
    newData.destination_id = newData.destinations;
    delete newData.query;
    delete newData.destinations;
    delete newData.is_favorite;
    delete newData.input_data;
  }
  return newData;
};

export class MLModel {
  constructor(model) {
    extend(this, model);

    if (!has(this, "options")) {
      this.options = {};
    }
    if (!has(this, "query")) {
      this.query = {};
    }
    if (!has(this, "destinations")) {
      this.destinations = [];
    }
    if (!has(this, "tags")) {
      this.tags = [];
    }
    if (!has(this, "user")) {
      this.user = currentUser;
    }
    if (!has(this, "version")) {
      this.version = 1;
    }
    if (!has(this, "description")) {
      this.description = "This model is awesome!";
    }
  }

  isNew() {
    return this.id === undefined;
  }

  getUrl() {
    return `ml_models/${this.id}`;
  }

  favorite() {
    return MLModel.favorite(this.id);
  }

  unfavorite() {
    return MLModel.unfavorite(this.id);
  }

  revertToVersion(versionNumber) {
    return MLModel.revertToVersion(this.id, versionNumber);
  }

  createFromVersion(versionNumber) {
    return MLModel.createFromVersion(this.id, versionNumber);
  }

  stop() {
    return MLModel.stopTraining(this.id);
  }
}

const saveOrCreateUrl = data => (data.id ? `api/ml_models/${data.id}` : "api/ml_models");

const MLModelService = {
  query: params => axios.get("api/ml_models", { params }),
  get: ({ id }) => axios.get(`api/ml_models/${id}`).then(transformResponse),
  delete: id => axios.delete(`api/ml_models/${id}`),
  recent: params => axios.get("api/ml_models/recent", { params }),
  archive: params => axios.get("api/ml_models/archive", { params }),
  myModels: params => axios.get("api/ml_models/my", { params }),
  favorites: params => axios.get("api/ml_models/favorites", { params }),
  favorite: id => axios.post(`api/ml_models/${id}/favorite`),
  unfavorite: id => axios.delete(`api/ml_models/${id}/favorite`),
  mute: data => axios.post(`api/ml_models/${data.id}/mute`),
  unmute: data => axios.delete(`api/ml_models/${data.id}/mute`),
  train: id => axios.post(`api/ml_models/${id}/train`),
  predict: id => axios.post(`api/ml_models/${id}/predict`),
  revertToVersion: (id, versionNumber) =>
    axios.post(`api/ml_models/${id}/revert`, { version: versionNumber }),
  createFromVersion: (id, versionNumber) =>
    axios.post(`api/ml_models/${id}/create_from_version`, { version: versionNumber }),
  copy: id => axios.post(`api/ml_models/${id}/copy`),
  getVersions: id => axios.get(`api/ml_models/${id}/versions`),
  getPredictions: id => axios.get(`api/ml_models/${id}/predictions`),
  stopTraining: id => axios.post(`api/ml_models/${id}/stop`),
  stopPredicting: id => axios.post(`api/ml_models/${id}/stop_predict`),
};

MLModelService.save = data =>
  axios.post(saveOrCreateUrl(data), transformRequest(data)).then(transformResponse);

MLModelService.newMLModel = function newMLModel() {
  return new MLModel({
    name: "New MLModel",
    query: null,
    options: {
      op_train: ">",
      column_train: null,
      op_predict: ">",
      column_predict: null,
      value_train: 0,
      value_predict: 0,
      regressor: "Regression",
      train_size: 0.75,
      test_size: 0.25,
      random_state: 42,
      features: [],
      targets: [],
      categories: [],
      timestamp: null,
      rearm_train: "never",
      rearm_predict: "never",
    },
    destinations: [],
    user: currentUser,
    tags: [],
    can_edit: true,
    version: 1,
    description: "This model is awesome!",
    state: "unknown",
    state_train: "unknown",
    state_predict: "unknown",
  });
};

extend(MLModel, MLModelService);

export default MLModel;
