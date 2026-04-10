import AsyncStorage from "@react-native-async-storage/async-storage";
import axios from "axios";
import { API_BASE_URL, API_TIMEOUT, STORAGE_KEYS } from "../constants/config";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

api.interceptors.request.use(
  async (config) => {
    try {
      const token = await AsyncStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (error) {
      console.error("Error retrieving auth token:", error);
    }
    return config;
  },
  (error) => Promise.reject(error),
);

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.code === "ECONNABORTED") {
      return Promise.reject({
        message: "Request timed out - please try again",
        status: 0,
      });
    }

    if (error.response) {
      const { status } = error.response;

      if (status === 401) {
        try {
          await AsyncStorage.multiRemove([
            STORAGE_KEYS.AUTH_TOKEN,
            STORAGE_KEYS.USER_DATA,
          ]);
        } catch (storageError) {
          console.error("Failed to clear auth storage:", storageError);
        }
      }

      return Promise.reject({
        message:
          error.response.data?.message ||
          error.response.data?.error ||
          "Server error occurred",
        status,
        data: error.response.data,
      });
    } else if (error.request) {
      return Promise.reject({
        message: "Network error - please check your connection",
        status: 0,
      });
    } else {
      return Promise.reject({
        message: error.message || "An unexpected error occurred",
        status: 0,
      });
    }
  },
);

export default api;
