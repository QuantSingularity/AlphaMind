import axios, { type AxiosError, type AxiosInstance } from "axios";
import type {
  AlternativeDataSource,
  ApiError,
  ApiResponse,
  BacktestResult,
  MarketData,
  Order,
  Portfolio,
  Position,
  RiskMetrics,
  Strategy,
} from "../types";

// Base URL: in development Vite proxies /api → backend; in production the
// Nginx ingress routes /api to the backend service. The /api/v1 prefix
// matches the backend router registration in app/main.py.
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

class ApiService {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        "Content-Type": "application/json",
      },
    });

    // Attach JWT on every request
    this.api.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem("authToken");
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error),
    );

    // Normalise error shape
    this.api.interceptors.response.use(
      (response) => response,
      (error: AxiosError<ApiError>) => {
        const apiError: ApiError = {
          message:
            error.response?.data?.message ||
            error.message ||
            "An error occurred",
          code: error.response?.data?.code || error.code || "UNKNOWN_ERROR",
          details: error.response?.data?.details,
        };
        return Promise.reject(apiError);
      },
    );
  }

  // ── Health ───────────────────────────────────────────────────────────────
  async healthCheck(): Promise<{ status: string }> {
    const response = await this.api.get("/health");
    return response.data;
  }

  // ── Strategies ───────────────────────────────────────────────────────────
  async getStrategies(): Promise<Strategy[]> {
    const response = await this.api.get<Strategy[]>("/api/v1/strategies/");
    return response.data;
  }

  async getStrategy(id: string): Promise<Strategy> {
    const response = await this.api.get<Strategy>(`/api/v1/strategies/${id}`);
    return response.data;
  }

  async getStrategyEquityCurve(
    id: string,
  ): Promise<{ strategyId: string; equityCurve: unknown[] }> {
    const response = await this.api.get(
      `/api/v1/strategies/${id}/equity-curve`,
    );
    return response.data;
  }

  async createStrategy(strategy: Partial<Strategy>): Promise<Strategy> {
    const response = await this.api.post<Strategy>(
      "/api/v1/strategies/",
      strategy,
    );
    return response.data;
  }

  async updateStrategy(
    id: string,
    strategy: Partial<Strategy>,
  ): Promise<Strategy> {
    const response = await this.api.put<Strategy>(
      `/api/v1/strategies/${id}`,
      strategy,
    );
    return response.data;
  }

  async deleteStrategy(id: string): Promise<void> {
    await this.api.delete(`/api/v1/strategies/${id}`);
  }

  async activateStrategy(id: string): Promise<Strategy> {
    const response = await this.api.post<Strategy>(
      `/api/v1/strategies/${id}/activate`,
    );
    return response.data;
  }

  async deactivateStrategy(id: string): Promise<Strategy> {
    const response = await this.api.post<Strategy>(
      `/api/v1/strategies/${id}/deactivate`,
    );
    return response.data;
  }

  // ── Market Data ──────────────────────────────────────────────────────────
  async getMarketData(
    ticker: string,
    interval?: string,
  ): Promise<MarketData[]> {
    const response = await this.api.get<MarketData[]>("/api/v1/market-data/", {
      params: { ticker, interval },
    });
    return response.data;
  }

  async getQuote(symbol: string): Promise<MarketData> {
    const response = await this.api.get<MarketData>(
      `/api/v1/market-data/quote/${symbol}`,
    );
    return response.data;
  }

  async getHistoricalData(
    symbol: string,
    days = 30,
    interval = "1d",
  ): Promise<MarketData[]> {
    const response = await this.api.get<MarketData[]>(
      `/api/v1/market-data/historical/${symbol}`,
      { params: { days, interval } },
    );
    return response.data;
  }

  async subscribeToMarketData(
    tickers: string[],
    callback: (data: MarketData) => void,
  ): Promise<() => void> {
    const intervalId = setInterval(async () => {
      for (const ticker of tickers) {
        try {
          const data = await this.getQuote(ticker);
          callback(data);
        } catch (error) {
          console.error(`Error fetching market data for ${ticker}:`, error);
        }
      }
    }, 5000);
    return () => clearInterval(intervalId);
  }

  // ── Portfolio ────────────────────────────────────────────────────────────
  async getPortfolio(): Promise<Portfolio> {
    const response = await this.api.get<Portfolio>("/api/v1/portfolio/");
    return response.data;
  }

  async getPortfolioPerformance(timeframe = "1M"): Promise<unknown> {
    const response = await this.api.get("/api/v1/portfolio/performance", {
      params: { timeframe },
    });
    return response.data;
  }

  async getPositions(): Promise<Position[]> {
    const response = await this.api.get<Position[]>(
      "/api/v1/portfolio/positions",
    );
    return response.data;
  }

  async getPosition(id: string): Promise<Position> {
    const response = await this.api.get<Position>(
      `/api/v1/portfolio/positions/${id}`,
    );
    return response.data;
  }

  async closePosition(id: string): Promise<void> {
    await this.api.post(`/api/v1/portfolio/positions/${id}/close`);
  }

  // ── Orders ───────────────────────────────────────────────────────────────
  async getOrders(): Promise<Order[]> {
    const response = await this.api.get<Order[]>("/api/v1/trading/orders");
    return response.data;
  }

  async createOrder(order: Partial<Order>): Promise<Order> {
    const response = await this.api.post<Order>(
      "/api/v1/trading/orders",
      order,
    );
    return response.data;
  }

  async cancelOrder(id: string): Promise<void> {
    await this.api.delete(`/api/v1/trading/orders/${id}`);
  }

  // ── Backtesting ──────────────────────────────────────────────────────────
  async runBacktest(
    strategyId: string,
    startDate: string,
    endDate: string,
    initialCapital: number,
  ): Promise<BacktestResult> {
    const response = await this.api.post<BacktestResult>("/api/v1/backtest/", {
      strategyId,
      startDate,
      endDate,
      initialCapital,
    });
    return response.data;
  }

  async getBacktestResults(strategyId: string): Promise<BacktestResult[]> {
    const response = await this.api.get<BacktestResult[]>(
      `/api/v1/backtest/${strategyId}`,
    );
    return response.data;
  }

  // ── Risk ─────────────────────────────────────────────────────────────────
  async getRiskMetrics(portfolioId?: string): Promise<RiskMetrics> {
    const response = await this.api.get<RiskMetrics>("/api/v1/risk/metrics", {
      params: portfolioId ? { portfolioId } : {},
    });
    return response.data;
  }

  async getStressScenarios(): Promise<unknown[]> {
    const response = await this.api.get("/api/v1/risk/stress-scenarios");
    return response.data;
  }

  async getCorrelationMatrix(): Promise<unknown[]> {
    const response = await this.api.get("/api/v1/risk/correlation-matrix");
    return response.data;
  }

  async getRiskRadar(): Promise<unknown[]> {
    const response = await this.api.get("/api/v1/risk/radar");
    return response.data;
  }

  // ── Alternative Data ─────────────────────────────────────────────────────
  async getAlternativeDataSources(): Promise<AlternativeDataSource[]> {
    const response = await this.api.get<AlternativeDataSource[]>(
      "/api/v1/alternative-data/sources",
    );
    return response.data;
  }

  async getAlternativeData(
    sourceId: string,
    params?: Record<string, unknown>,
  ): Promise<unknown> {
    const response = await this.api.get(
      `/api/v1/alternative-data/${sourceId}`,
      { params },
    );
    return response.data;
  }
}

export const apiService = new ApiService();
export default apiService;
