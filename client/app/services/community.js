import { axios } from "@/services/axios";

export const COMMUNITY_CATEGORIES = [
  { value: "general", label: "General", icon: "fa-comments" },
  { value: "queries", label: "Queries", icon: "fa-code" },
  { value: "dashboards", label: "Dashboards", icon: "fa-th-large" },
  { value: "alerts", label: "Alerts", icon: "fa-bell" },
  { value: "tips", label: "Tips & tricks", icon: "fa-lightbulb-o" },
];

export function getCategoryMeta(category) {
  return COMMUNITY_CATEGORIES.find(item => item.value === category) || COMMUNITY_CATEGORIES[0];
}

const Community = {
  list: ({ category, q, limit, page, pageSize } = {}) =>
    axios.get("api/community/posts", {
      params: {
        category: category || undefined,
        q: q || undefined,
        limit,
        page,
        page_size: pageSize,
      },
    }),
  get: postId => axios.get(`api/community/posts/${postId}`),
  create: payload => axios.post("api/community/posts", payload),
  save: (postId, payload) => axios.post(`api/community/posts/${postId}`, payload),
  delete: postId => axios.delete(`api/community/posts/${postId}`),
};

export default Community;
