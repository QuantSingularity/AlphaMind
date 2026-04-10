import portfolioReducer, {
  clearError,
  fetchHoldings,
  fetchPerformance,
  fetchPortfolio,
  resetPortfolio,
} from "../../store/slices/portfolioSlice";
import { logoutUser } from "../../store/slices/authSlice";

describe("portfolioSlice", () => {
  const initialState = {
    data: null,
    performance: [],
    holdings: [],
    loading: false,
    performanceLoading: false,
    holdingsLoading: false,
    error: null,
    lastUpdated: null,
  };

  it("should return initial state", () => {
    expect(portfolioReducer(undefined, { type: "unknown" })).toEqual(
      initialState,
    );
  });

  it("should handle clearError", () => {
    const state = { ...initialState, error: "Some error" };
    expect(portfolioReducer(state, clearError())).toMatchObject({
      error: null,
    });
  });

  it("should handle resetPortfolio", () => {
    const state = {
      ...initialState,
      data: { value: 100 },
      error: "error",
    };
    expect(portfolioReducer(state, resetPortfolio())).toEqual(initialState);
  });

  it("should handle fetchPortfolio.pending", () => {
    const state = portfolioReducer(initialState, {
      type: fetchPortfolio.pending.type,
    });
    expect(state.loading).toBe(true);
    expect(state.error).toBeNull();
  });

  it("should handle fetchPortfolio.fulfilled", () => {
    const mockData = { value: 1250000, dailyPnL: 5000 };
    const state = portfolioReducer(initialState, {
      type: fetchPortfolio.fulfilled.type,
      payload: mockData,
    });
    expect(state.loading).toBe(false);
    expect(state.data).toEqual(mockData);
    expect(state.lastUpdated).not.toBeNull();
    expect(state.error).toBeNull();
  });

  it("should handle fetchPortfolio.rejected", () => {
    const state = portfolioReducer(initialState, {
      type: fetchPortfolio.rejected.type,
      payload: "Fetch failed",
    });
    expect(state.loading).toBe(false);
    expect(state.error).toBe("Fetch failed");
  });

  it("should handle fetchPerformance.pending", () => {
    const state = portfolioReducer(initialState, {
      type: fetchPerformance.pending.type,
    });
    expect(state.performanceLoading).toBe(true);
  });

  it("should handle fetchPerformance.fulfilled", () => {
    const perfData = [{ date: "2025-01-01", value: 1000000 }];
    const state = portfolioReducer(initialState, {
      type: fetchPerformance.fulfilled.type,
      payload: perfData,
    });
    expect(state.performanceLoading).toBe(false);
    expect(state.performance).toEqual(perfData);
  });

  it("should handle fetchHoldings.pending", () => {
    const state = portfolioReducer(initialState, {
      type: fetchHoldings.pending.type,
    });
    expect(state.holdingsLoading).toBe(true);
  });

  it("should handle fetchHoldings.fulfilled", () => {
    const holdings = [{ symbol: "AAPL", shares: 100, value: 18000 }];
    const state = portfolioReducer(initialState, {
      type: fetchHoldings.fulfilled.type,
      payload: holdings,
    });
    expect(state.holdingsLoading).toBe(false);
    expect(state.holdings).toEqual(holdings);
  });

  it("should reset on logoutUser.fulfilled", () => {
    const populatedState = {
      ...initialState,
      data: { value: 999999 },
      holdings: [{ symbol: "TSLA" }],
    };
    const state = portfolioReducer(populatedState, {
      type: logoutUser.fulfilled.type,
    });
    expect(state).toEqual(initialState);
  });

  it("should reset on logoutUser.rejected", () => {
    const populatedState = {
      ...initialState,
      data: { value: 999999 },
    };
    const state = portfolioReducer(populatedState, {
      type: logoutUser.rejected.type,
    });
    expect(state).toEqual(initialState);
  });
});
