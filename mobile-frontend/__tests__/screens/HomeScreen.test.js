import { configureStore } from "@reduxjs/toolkit";
import { render, screen } from "@testing-library/react-native";
import { Provider as PaperProvider } from "react-native-paper";
import { Provider } from "react-redux";
import HomeScreen from "../../screens/HomeScreen";
import authReducer from "../../store/slices/authSlice";
import portfolioReducer from "../../store/slices/portfolioSlice";
import settingsReducer from "../../store/slices/settingsSlice";

const mockPortfolioData = {
  value: 1250345.67,
  dailyPnL: 15678.9,
  dailyPnLPercent: 1.27,
  sharpeRatio: 2.35,
  activeStrategies: 12,
};

const createMockStore = (portfolioData = null, authUser = null) =>
  configureStore({
    reducer: {
      auth: authReducer,
      portfolio: portfolioReducer,
      settings: settingsReducer,
    },
    preloadedState: {
      auth: {
        user: authUser,
        isAuthenticated: !!authUser,
        loading: false,
        error: null,
      },
      portfolio: {
        data: portfolioData,
        performance: [],
        holdings: [],
        loading: false,
        performanceLoading: false,
        holdingsLoading: false,
        error: null,
        lastUpdated: null,
      },
      settings: {
        theme: "light",
        notifications: {
          tradeAlerts: true,
          researchUpdates: true,
          priceAlerts: true,
        },
        displayPreferences: {
          currency: "USD",
          decimalPlaces: 2,
          chartType: "line",
        },
      },
    },
  });

const renderWithProviders = (store) =>
  render(
    <Provider store={store}>
      <PaperProvider>
        <HomeScreen />
      </PaperProvider>
    </Provider>,
  );

describe("HomeScreen", () => {
  it("renders the dashboard title", () => {
    renderWithProviders(createMockStore());
    expect(screen.getByText("Dashboard")).toBeTruthy();
  });

  it("shows welcome message with user name when logged in", () => {
    const store = createMockStore(null, {
      name: "John Doe",
      email: "john@example.com",
    });
    renderWithProviders(store);
    expect(screen.getByText("John Doe")).toBeTruthy();
    expect(screen.getByText("Welcome back, ")).toBeTruthy();
  });

  it("shows welcome with email when name not set", () => {
    const store = createMockStore(null, {
      email: "john@example.com",
    });
    renderWithProviders(store);
    expect(screen.getByText("john@example.com")).toBeTruthy();
  });

  it("renders all KPI card titles", () => {
    renderWithProviders(createMockStore());
    expect(screen.getByText("Portfolio Value")).toBeTruthy();
    expect(screen.getByText("Daily P&L")).toBeTruthy();
    expect(screen.getByText("Sharpe Ratio")).toBeTruthy();
    expect(screen.getByText("Active Strategies")).toBeTruthy();
  });

  it("renders KPI cards with zero values when no data", () => {
    renderWithProviders(createMockStore());
    expect(screen.getByText("$0.00")).toBeTruthy();
    expect(screen.getAllByText("0.0%")).toHaveLength(2);
  });

  it("renders KPI cards with portfolio data", () => {
    const store = createMockStore(mockPortfolioData);
    renderWithProviders(store);
    expect(screen.getByText("12")).toBeTruthy();
    expect(screen.getByText("2.35")).toBeTruthy();
  });

  it("shows subtitle text", () => {
    renderWithProviders(createMockStore());
    expect(
      screen.getByText("Real-time quantitative trading overview"),
    ).toBeTruthy();
  });

  it("shows performance section label", () => {
    renderWithProviders(createMockStore());
    expect(screen.getByText("Performance")).toBeTruthy();
  });
});
