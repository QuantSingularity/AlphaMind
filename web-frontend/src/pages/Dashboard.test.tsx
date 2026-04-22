import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { Dashboard } from "./Dashboard";

// ── Mock the API service so tests run without a live backend ─────────────
vi.mock("../services/api", () => ({
  default: {
    getPortfolio: vi.fn().mockResolvedValue({
      id: "port-001",
      name: "Test Portfolio",
      totalValue: 125430.5,
      cash: 25430.5,
      dailyPnL: 2340.25,
      totalPnL: 25430.5,
      allocation: [
        { ticker: "AAPL", value: 17550, percentage: 14.0 },
        { ticker: "MSFT", value: 16900, percentage: 13.5 },
      ],
    }),
    getPositions: vi.fn().mockResolvedValue([
      {
        id: "pos-001",
        ticker: "AAPL",
        sector: "Technology",
        quantity: 100,
        entryPrice: 150.0,
        currentPrice: 175.5,
        unrealizedPnL: 2550.0,
        realizedPnL: 0.0,
        weight: 0.28,
        beta: 1.21,
        sharpeContrib: 0.42,
        var95: 1240,
        timestamp: "2024-01-01T00:00:00Z",
      },
    ]),
    getPortfolioPerformance: vi.fn().mockResolvedValue({
      equityCurve: [
        { timestamp: "2024-01-01", value: 100000 },
        { timestamp: "2024-01-02", value: 101000 },
      ],
      metrics: {
        sharpeRatio: 2.31,
        maxDrawdown: -0.089,
        annualisedReturn: 0.384,
        volatility: 0.142,
        alpha: 0.094,
        beta: 0.88,
        totalReturn: 0.254,
        winRate: 0.64,
      },
    }),
  },
  apiService: {},
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe("Dashboard Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders dashboard header", async () => {
    render(<Dashboard />, { wrapper: createWrapper() });
    expect(await screen.findByText("Trading Dashboard")).toBeInTheDocument();
  });

  it("displays portfolio metrics cards", async () => {
    render(<Dashboard />, { wrapper: createWrapper() });
    expect(await screen.findByText("Total Value")).toBeInTheDocument();
    expect(await screen.findByText("Daily P&L")).toBeInTheDocument();
    expect(await screen.findByText("Cash")).toBeInTheDocument();
  });

  it("displays positions table", async () => {
    render(<Dashboard />, { wrapper: createWrapper() });
    // Updated label matches Dashboard.tsx v2: "Open Positions (N)"
    expect(await screen.findByText(/Open Positions/)).toBeInTheDocument();
  });

  it("displays equity curve section", async () => {
    render(<Dashboard />, { wrapper: createWrapper() });
    expect(await screen.findByText(/Equity Curve/)).toBeInTheDocument();
  });
});
