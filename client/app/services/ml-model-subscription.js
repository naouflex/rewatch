import { axios } from "@/services/axios";

const MLModelSubscription = {
  query: ({ modelId }) => axios.get(`api/ml_models/${modelId}/subscriptions`),
  create: data => axios.post(`api/ml_models/${data.model_id}/subscriptions`, data),
  delete: data => axios.delete(`api/ml_models/${data.model_id}/subscriptions/${data.id}`),
};

export default MLModelSubscription;
