import { axios } from "@/services/axios";
import { extend, has, merge } from "lodash";
import { currentUser } from "@/services/auth";

const transformResponse = data =>
  merge({}, data, {
    query: data.query || {},
    model: data.model || {},
    destinations: data.destinations || [],
    tags: data.tags || [],
    user: data.user || currentUser,
  });

const transformRequest = data => {
  const newData = Object.assign({}, data);
  if (newData.query_id === undefined) {
    newData.query_id = newData.query && newData.query.id;
    newData.model_id = newData.model && newData.model.id;
    delete newData.query;
    delete newData.model;
    delete newData.is_favorite;
  }
  return newData;
};

export class PredictionResult {
  constructor(prediction) {
    extend(this, prediction);

    if (!has(this, "model")) {
      this.model = {};
    }
    if (!has(this, "query")) {
      this.query = {};
    }
    if (!has(this, "tags")) {
      this.tags = [];
    }
    if (!has(this, "user")) {
      this.user = currentUser;
    }
    if (!has(this, "destinations")) {
      this.destinations = [];
    }
  }

  isNew() {
    return this.id === undefined;
  }

  getUrl() {
    return `predictions/${this.id}`;
  }

  favorite() {
    return PredictionResult.favorite(this.id);
  }

  unfavorite() {
    return PredictionResult.unfavorite(this.id);
  }
}

const saveOrCreateUrl = data => (data.id ? `api/predictions/${data.id}` : "api/predictions");

const PredictionResultService = {
  query: params => axios.get("api/predictions", { params }),
  get: ({ id }) => axios.get(`api/predictions/${id}`).then(transformResponse),
  delete: id => axios.delete(`api/predictions/${id}`),
  recent: params => axios.get("api/predictions/recent", { params }),
  archive: params => axios.get("api/predictions/archive", { params }),
  myPredictionResults: params => axios.get("api/predictions/my", { params }),
  favorites: params => axios.get("api/predictions/favorites", { params }),
  favorite: id => axios.post(`api/predictions/${id}/favorite`),
  unfavorite: id => axios.delete(`api/predictions/${id}/favorite`),
  get_from_model_id: ({ id }) => axios.get(`api/ml_models/${id}/predictions`),
};

PredictionResultService.save = data =>
  axios.post(saveOrCreateUrl(data), transformRequest(data)).then(transformResponse);

extend(PredictionResult, PredictionResultService);

export default PredictionResult;
