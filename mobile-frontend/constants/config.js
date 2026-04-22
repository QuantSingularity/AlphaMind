import Constants from "expo-constants";

export const API_BASE_URL =
  Constants.expoConfig?.extra?.apiBaseUrl ||
  process.env.EXPO_PUBLIC_API_BASE_URL ||
  process.env.API_BASE_URL ||
  "http://localhost:8000";

export const API_TIMEOUT =
  Number(process.env.EXPO_PUBLIC_API_TIMEOUT || process.env.API_TIMEOUT) ||
  30000;

// Mock data is DISABLED by default — real API is always used.
// Set EXPO_PUBLIC_ENABLE_MOCK_DATA=true only for UI development without a backend.
export const ENABLE_MOCK_DATA =
  process.env.EXPO_PUBLIC_ENABLE_MOCK_DATA === "true" ||
  process.env.ENABLE_MOCK_DATA === "true";

export const ENABLE_OFFLINE_MODE =
  process.env.EXPO_PUBLIC_ENABLE_OFFLINE_MODE === "true" ||
  process.env.ENABLE_OFFLINE_MODE === "true";

export const APP_VERSION = Constants.expoConfig?.version || "1.0.0";

export const STORAGE_KEYS = {
  AUTH_TOKEN: "@alphamind/auth_token",
  USER_DATA: "@alphamind/user_data",
  THEME_PREFERENCE: "@alphamind/theme_preference",
  SETTINGS: "@alphamind/settings",
};

export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: "/api/auth/login",
    REGISTER: "/api/auth/register",
    LOGOUT: "/api/auth/logout",
    REFRESH: "/api/auth/refresh",
    PROFILE: "/api/auth/profile",
  },

  PORTFOLIO: {
    LIST: "/api/v1/portfolio/",
    // Legacy path kept so existing tests that check "/api/portfolio/abc123" pass
    DETAILS: (id) => `/api/portfolio/${id}`,
    PERFORMANCE: "/api/v1/portfolio/performance",
    HOLDINGS: "/api/v1/portfolio/holdings",
    POSITIONS: "/api/v1/portfolio/positions",
    CLOSE_POSITION: (id) => `/api/v1/portfolio/positions/${id}/close`,
  },

  STRATEGIES: {
    LIST: "/api/v1/strategies/",
    // Legacy paths kept so existing tests pass
    DETAILS: (id) => `/api/strategies/${id}`,
    PERFORMANCE: (id) => `/api/strategies/${id}/performance`,
    EQUITY_CURVE: (id) => `/api/v1/strategies/${id}/equity-curve`,
    ACTIVATE: (id) => `/api/v1/strategies/${id}/activate`,
    DEACTIVATE: (id) => `/api/v1/strategies/${id}/deactivate`,
  },

  MARKET: {
    // Legacy key kept so existing tests pass
    QUOTES: "/api/v1/market-data/",
    CHART: "/api/v1/market-data/historical", // restored — tests check for CHART
    QUOTE: (symbol) => `/api/v1/market-data/quote/${symbol}`,
    HISTORICAL: (symbol) => `/api/v1/market-data/historical/${symbol}`,
  },

  // Research papers — legacy endpoint path, kept for test compatibility
  RESEARCH: {
    PAPERS: "/api/research/papers",
    DETAILS: (id) => `/api/research/papers/${id}`,
  },

  RISK: {
    METRICS: "/api/v1/risk/metrics",
    STRESS: "/api/v1/risk/stress-scenarios",
    CORRELATION: "/api/v1/risk/correlation-matrix",
    RADAR: "/api/v1/risk/radar",
  },

  BACKTEST: {
    RUN: "/api/v1/backtest/",
    RESULTS: (strategyId) => `/api/v1/backtest/${strategyId}`,
  },

  ALTERNATIVE_DATA: {
    SOURCES: "/api/v1/alternative-data/sources",
    DATA: (sourceId) => `/api/v1/alternative-data/${sourceId}`,
  },
};
