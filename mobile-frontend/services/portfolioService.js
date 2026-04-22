import { API_ENDPOINTS } from "../constants/config";
import api from "./api";

export const portfolioService = {
  /**
   * Get portfolio overview (total value, P&L, allocations)
   */
  getPortfolio: async () => {
    const response = await api.get(API_ENDPOINTS.PORTFOLIO.LIST);
    return response.data;
  },

  /**
   * Get portfolio performance data for a given timeframe (1W, 1M, 3M, 6M, 1Y)
   */
  getPerformance: async (timeframe = "1M") => {
    const response = await api.get(API_ENDPOINTS.PORTFOLIO.PERFORMANCE, {
      params: { timeframe },
    });
    return response.data;
  },

  /**
   * Get simplified holdings list (symbol, shares, value, weight)
   */
  getHoldings: async () => {
    const response = await api.get(API_ENDPOINTS.PORTFOLIO.HOLDINGS);
    return response.data;
  },

  /**
   * Get all open positions with full risk metadata
   */
  getPositions: async () => {
    const response = await api.get(API_ENDPOINTS.PORTFOLIO.POSITIONS);
    return response.data;
  },

  /**
   * Close a position by ID
   */
  closePosition: async (positionId) => {
    const response = await api.post(
      API_ENDPOINTS.PORTFOLIO.CLOSE_POSITION(positionId),
    );
    return response.data;
  },

  /**
   * Get portfolio details by ID (for deep-link / shared portfolio views)
   */
  getPortfolioDetails: async (id) => {
    const response = await api.get(API_ENDPOINTS.PORTFOLIO.DETAILS(id));
    return response.data;
  },
};
