import axios from "axios";

const API = "https://your-backend-url";

export const login = (data) => axios.post(API + "/admin/login", data);

export const getOrders = (token) =>
  axios.get(API + "/admin/orders", {
    headers: { Authorization: "Bearer " + token },
  });

export const confirmOrder = (id, token) =>
  axios.post(API + "/admin/confirm/" + id, {}, {
    headers: { Authorization: "Bearer " + token },
  });
