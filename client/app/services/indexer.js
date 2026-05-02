import { axios } from "@/services/axios";
import { extend, map } from "lodash";

export class Indexer {
  constructor(indexer) {
    extend(this, indexer);
  }

  favorite() {
    return IndexerService.favorite(this);
  }

  unfavorite() {
    return IndexerService.unfavorite(this);
  }
}

const wrap = indexer => new Indexer(indexer);
const wrapList = list => map(list, wrap);

const saveOrCreateUrl = data => (data.id ? `api/indexers/${data.id}` : "api/indexers");

const IndexerService = {
  query: () => axios.get("api/indexers").then(wrapList),
  myIndexers: () => axios.get("api/indexers/my").then(wrapList),
  favorites: () => axios.get("api/indexers/favorites").then(wrapList),
  archive: () => axios.get("api/indexers/archive").then(wrapList),
  tags: () => axios.get("api/indexers/tags"),
  get: ({ id }) => axios.get(`api/indexers/${id}`).then(wrap),
  save: data => axios.post(saveOrCreateUrl(data), data).then(wrap),
  delete: data => axios.delete(`api/indexers/${data.id}`),
  doArchive: data => axios.post(`api/indexers/${data.id}/archive`).then(wrap),
  favorite: data => axios.post(`api/indexers/${data.id}/favorite`),
  unfavorite: data => axios.delete(`api/indexers/${data.id}/favorite`),
};

export default IndexerService;
