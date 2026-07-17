import axios from "axios";

const configuredBackendUrl =
  process.env.REACT_APP_BACKEND_URL?.trim().replace(/\/+$/, "") || "";

export const API = configuredBackendUrl
  ? `${configuredBackendUrl}/api`
  : "/api";

export const api = axios.create({
  baseURL: API,
  timeout: 600000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("cs_token");

  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

export const authApi = {
  register: (data) =>
    api.post("/auth/register", data).then((response) => response.data),

  login: (data) =>
    api.post("/auth/login", data).then((response) => response.data),

  me: () =>
    api.get("/auth/me").then((response) => response.data),
};

export const csApi = {
  clean: (payload) =>
    api.post("/clean", payload).then((response) => response.data),

  analyze: (payload) =>
    api.post("/analyze", payload).then((response) => response.data),

  trace: (payload) =>
    api.post("/trace", payload).then((response) => response.data),

  history: () =>
    api.get("/history").then((response) => response.data),

  getHistory: (id) =>
    api.get(`/history/${id}`).then((response) => response.data),

  deleteHistory: (id) =>
    api.delete(`/history/${id}`).then((response) => response.data),

  extract: (file) => {
    const formData = new FormData();
    formData.append("file", file);

    return api
      .post("/extract", formData)
      .then((response) => response.data);
  },
};