import { portfolioService } from "../../services/portfolioService";

jest.mock("../../services/api", () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
  },
}));

jest.mock("../../constants/config", () => ({
  API_ENDPOINTS: {
    PORTFOLIO: {
      LIST: "/api/portfolio",
      PERFORMANCE: "/api/portfolio/performance",
      HOLDINGS: "/api/portfolio/holdings",
      DETAILS: (id) => `/api/portfolio/${id}`,
    },
  },
  ENABLE_MOCK_DATA: false,
}));

import api from "../../services/api";

describe("portfolioService", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("getPortfolio", () => {
    it("fetches portfolio data from API", async () => {
      const mockData = { value: 1250000, dailyPnL: 5000 };
      api.get.mockResolvedValueOnce({ data: mockData });

      const result = await portfolioService.getPortfolio();
      expect(api.get).toHaveBeenCalledWith("/api/portfolio");
      expect(result).toEqual(mockData);
    });

    it("propagates API errors", async () => {
      api.get.mockRejectedValueOnce({ message: "Server error" });
      await expect(portfolioService.getPortfolio()).rejects.toEqual({
        message: "Server error",
      });
    });
  });

  describe("getPerformance", () => {
    it("fetches performance with timeframe param", async () => {
      const mockPerf = [{ date: "2025-01-01", value: 1000000 }];
      api.get.mockResolvedValueOnce({ data: mockPerf });

      const result = await portfolioService.getPerformance("3M");
      expect(api.get).toHaveBeenCalledWith("/api/portfolio/performance", {
        params: { timeframe: "3M" },
      });
      expect(result).toEqual(mockPerf);
    });

    it("uses default timeframe of 1M", async () => {
      api.get.mockResolvedValueOnce({ data: [] });
      await portfolioService.getPerformance();
      expect(api.get).toHaveBeenCalledWith("/api/portfolio/performance", {
        params: { timeframe: "1M" },
      });
    });
  });

  describe("getHoldings", () => {
    it("fetches holdings from API", async () => {
      const mockHoldings = [{ symbol: "AAPL", shares: 100, value: 18000 }];
      api.get.mockResolvedValueOnce({ data: mockHoldings });

      const result = await portfolioService.getHoldings();
      expect(api.get).toHaveBeenCalledWith("/api/portfolio/holdings");
      expect(result).toEqual(mockHoldings);
    });
  });

  describe("getPortfolioDetails", () => {
    it("fetches portfolio details by ID", async () => {
      const mockDetails = { id: "abc123", name: "Main Portfolio" };
      api.get.mockResolvedValueOnce({ data: mockDetails });

      const result = await portfolioService.getPortfolioDetails("abc123");
      expect(api.get).toHaveBeenCalledWith("/api/portfolio/abc123");
      expect(result).toEqual(mockDetails);
    });
  });
});
