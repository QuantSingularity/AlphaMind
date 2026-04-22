import { API_ENDPOINTS } from "../constants/config";
import api from "./api";

export const researchService = {
  // ── Research papers (legacy endpoints kept for backward compat) ──────────

  /**
   * Get research papers with optional filters.
   * Uses the legacy /api/research/papers path that the existing test suite covers.
   */
  getPapers: async (filters = {}) => {
    const response = await api.get(API_ENDPOINTS.RESEARCH.PAPERS, {
      params: filters,
    });
    return response.data;
  },

  /**
   * Get a single research paper by ID.
   */
  getPaperDetails: async (id) => {
    const response = await api.get(API_ENDPOINTS.RESEARCH.DETAILS(id));
    return response.data;
  },

  // ── Alternative data (v1 endpoints) ─────────────────────────────────────

  getAlternativeDataSources: async () => {
    const response = await api.get(API_ENDPOINTS.ALTERNATIVE_DATA.SOURCES);
    return response.data;
  },

  getAlternativeData: async (sourceId, params = {}) => {
    const response = await api.get(
      API_ENDPOINTS.ALTERNATIVE_DATA.DATA(sourceId),
      { params },
    );
    return response.data;
  },

  // ── Risk ─────────────────────────────────────────────────────────────────

  getRiskMetrics: async () => {
    const response = await api.get(API_ENDPOINTS.RISK.METRICS);
    return response.data;
  },

  getStressScenarios: async () => {
    const response = await api.get(API_ENDPOINTS.RISK.STRESS);
    return response.data;
  },

  // ── Strategies ───────────────────────────────────────────────────────────

  getStrategies: async () => {
    const response = await api.get(API_ENDPOINTS.STRATEGIES.LIST);
    return response.data;
  },

  // ── Backtest ─────────────────────────────────────────────────────────────

  runBacktest: async (strategyId, startDate, endDate, initialCapital) => {
    const response = await api.post(API_ENDPOINTS.BACKTEST.RUN, {
      strategyId,
      startDate,
      endDate,
      initialCapital,
    });
    return response.data;
  },
};
