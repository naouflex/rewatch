import { axios } from "@/services/axios";

const AlertEvents = {
  forAlert: ({ alertId, includeArchived = false, page = 1, pageSize = 20 } = {}) =>
    axios.get(`api/alerts/${alertId}/events`, {
      params: { include_archived: includeArchived, page, page_size: pageSize },
    }),
  get: ({ alertId, eventId }) => axios.get(`api/alerts/${alertId}/events/${eventId}`),
  archive: ({ alertId, eventId }) => axios.post(`api/alerts/${alertId}/events/${eventId}`),
  delete: ({ alertId, eventId }) => axios.delete(`api/alerts/${alertId}/events/${eventId}`),
  feed: ({ includeArchived = false, limit = 50 } = {}) =>
    axios.get("api/alert_events", {
      params: { include_archived: includeArchived, limit },
    }),
};

export default AlertEvents;
