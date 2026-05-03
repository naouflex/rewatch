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
      op: normalizeCondition[data.options.op] || data.options.op,
      regressor: data.options.regressor || "Regression",
      train_size: data.options.train_size || 0.75,
      test_size: data.options.test_size || 0.25,
      random_state: data.options.random_state || 42,
      features: data.options.features || [],
      targets: data.options.targets || [],
      categories: data.options.categories || [],
      timestamp: data.options.timestamp || null,
    },
    query: data.query || {},
    destinations: data.destinations || [],
    tags: data.tags || [],
    user: data.user || currentUser,
    version: data.version || 1,
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
  }
  return newData;
};

export class MLModelVersion {
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
    return `ml_models_versions/${this.id}`;
  }

  favorite() {
    return MLModelVersion.favorite(this.id);
  }

  unfavorite() {
    return MLModelVersion.unfavorite(this.id);
  }
}

const saveOrCreateUrl = data =>
  data.id ? `api/ml_models_versions/${data.id}` : "api/ml_models_versions";

const MLModelVersionService = {
  query: params => axios.get("api/ml_models_versions", { params }),
  get: ({ id }) => axios.get(`api/ml_models_versions/${id}`).then(transformResponse),
  delete: id => axios.delete(`api/ml_models_versions/${id}`),
  recent: params => axios.get("api/ml_models_versions/recent", { params }),
  archive: params => axios.get("api/ml_models_versions/archive", { params }),
  myModelsVersions: params => axios.get("api/ml_models_versions/my", { params }),
  favorites: params => axios.get("api/ml_models_versions/favorites", { params }),
  favorite: id => axios.post(`api/ml_models_versions/${id}/favorite`),
  unfavorite: id => axios.delete(`api/ml_models_versions/${id}/favorite`),
};

MLModelVersionService.save = data =>
  axios.post(saveOrCreateUrl(data), transformRequest(data)).then(transformResponse);

extend(MLModelVersion, MLModelVersionService);

export default MLModelVersion;
