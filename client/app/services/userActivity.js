import { axios } from "@/services/axios";

const UserActivity = {
  getSummary: ({ days = 365 } = {}) => axios.get("api/users/me/activity", { params: { days } }),
};

export default UserActivity;
