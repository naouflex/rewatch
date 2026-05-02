import { axios } from "@/services/axios";
import { extend, map, merge } from "lodash";

// backwards compatibility
const normalizeCondition = {
  "greater than": ">",
  "less than": "<",
  equals: "=",
};

const transformResponse = data =>
  merge({}, data, {
    options: {
      op: normalizeCondition[data.options.op] || data.options.op,
    },
  });

const transformRequest = data => {
  const newData = Object.assign({}, data);
  if (newData.query_id === undefined) {
    newData.query_id = newData.query.id;
    newData.destination_id = newData.destinations;
    delete newData.query;
    delete newData.destinations;
  }

  return newData;
};

const saveOrCreateUrl = data => (data.id ? `api/alerts/${data.id}` : "api/alerts");

export class Alert {
  constructor(alert) {
    extend(this, alert);
  }

  favorite() {
    return AlertService.favorite(this);
  }

  unfavorite() {
    return AlertService.unfavorite(this);
  }
}

const wrap = alert => new Alert(alert);
const wrapList = list => map(list, wrap);

const AlertService = {
  query: () => axios.get("api/alerts").then(wrapList),
  myAlerts: () => axios.get("api/alerts/my").then(wrapList),
  favorites: () => axios.get("api/alerts/favorites").then(wrapList),
  archive: () => axios.get("api/alerts/archive").then(wrapList),
  tags: () => axios.get("api/alerts/tags"),
  get: ({ id }) => axios.get(`api/alerts/${id}`).then(transformResponse),
  save: data => axios.post(saveOrCreateUrl(data), transformRequest(data)),
  delete: data => axios.delete(`api/alerts/${data.id}`),
  mute: data => axios.post(`api/alerts/${data.id}/mute`),
  unmute: data => axios.delete(`api/alerts/${data.id}/mute`),
  evaluate: data => axios.post(`api/alerts/${data.id}/eval`),
  doArchive: data => axios.post(`api/alerts/${data.id}/archive`),
  favorite: data => axios.post(`api/alerts/${data.id}/favorite`),
  unfavorite: data => axios.delete(`api/alerts/${data.id}/favorite`),
};

export default AlertService;
