import { axios } from "@/services/axios";
import { extend, map } from "lodash";

export class QuerySnippet {
  constructor(querySnippet) {
    extend(this, querySnippet);
  }

  getSnippet() {
    let name = this.trigger;
    if (this.description !== "") {
      name = `${this.trigger}: ${this.description}`;
    }
    if (this.is_favorite) {
      name = `★ ${name}`;
    }

    return {
      name,
      content: this.snippet,
      tabTrigger: this.trigger,
    };
  }

  favorite() {
    return QuerySnippetService.favorite(this);
  }

  unfavorite() {
    return QuerySnippetService.unfavorite(this);
  }
}

const wrap = querySnippet => new QuerySnippet(querySnippet);
const wrapList = list => map(list, wrap);

const QuerySnippetService = {
  get: data => axios.get(`api/query_snippets/${data.id}`).then(wrap),
  query: () => axios.get("api/query_snippets").then(wrapList),
  myQuerySnippets: () => axios.get("api/query_snippets/my").then(wrapList),
  favorites: () => axios.get("api/query_snippets/favorites").then(wrapList),
  archive: () => axios.get("api/query_snippets/archive").then(wrapList),
  tags: () => axios.get("api/query_snippets/tags"),
  create: data => axios.post("api/query_snippets", data).then(wrap),
  save: data => axios.post(`api/query_snippets/${data.id}`, data).then(wrap),
  delete: data => axios.delete(`api/query_snippets/${data.id}`),
  doArchive: data => axios.post(`api/query_snippets/${data.id}/archive`).then(wrap),
  favorite: data => axios.post(`api/query_snippets/${data.id}/favorite`),
  unfavorite: data => axios.delete(`api/query_snippets/${data.id}/favorite`),
};

export default QuerySnippetService;
