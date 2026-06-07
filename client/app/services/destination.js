import { axios } from "@/services/axios";
import { extend, map } from "lodash";

export const IMG_ROOT = "static/images/destinations";

export class Destination {
  constructor(destination) {
    extend(this, destination);
  }

  favorite() {
    return DestinationService.favorite(this);
  }

  unfavorite() {
    return DestinationService.unfavorite(this);
  }
}

const wrap = destination => new Destination(destination);
const wrapList = list => map(list, wrap);

const DestinationService = {
  query: () => axios.get("api/destinations").then(wrapList),
  myDestinations: () => axios.get("api/destinations/my").then(wrapList),
  favorites: () => axios.get("api/destinations/favorites").then(wrapList),
  archive: () => axios.get("api/destinations/archive").then(wrapList),
  tags: () => axios.get("api/destinations/tags"),
  get: ({ id }) => axios.get(`api/destinations/${id}`),
  types: () => axios.get("api/destinations/types"),
  create: data => axios.post(`api/destinations`, data),
  save: data => axios.post(`api/destinations/${data.id}`, data),
  delete: ({ id }) => axios.delete(`api/destinations/${id}`),
  doArchive: data => axios.post(`api/destinations/${data.id}/archive`).then(wrap),
  favorite: data => axios.post(`api/destinations/${data.id}/favorite`),
  unfavorite: data => axios.delete(`api/destinations/${data.id}/favorite`),
};

export default DestinationService;
