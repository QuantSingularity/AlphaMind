import { configureStore } from "@reduxjs/toolkit";
import {
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react-native";
import { Provider as PaperProvider } from "react-native-paper";
import { Provider } from "react-redux";
import SettingsScreen from "../../screens/SettingsScreen";
import authReducer from "../../store/slices/authSlice";
import settingsReducer from "../../store/slices/settingsSlice";

jest.mock("../../store/settingsListener", () => ({
  settingsListenerMiddleware: {
    middleware: () => (next) => (action) => next(action),
  },
}));

const createMockStore = (authUser = null, settingsOverride = {}) =>
  configureStore({
    reducer: {
      auth: authReducer,
      settings: settingsReducer,
    },
    preloadedState: {
      auth: {
        user: authUser,
        isAuthenticated: !!authUser,
        loading: false,
        error: null,
      },
      settings: {
        theme: "system",
        notifications: {
          tradeAlerts: true,
          researchUpdates: true,
          priceAlerts: false,
        },
        displayPreferences: {
          currency: "USD",
          decimalPlaces: 2,
          chartType: "line",
        },
        ...settingsOverride,
      },
    },
  });

const renderWithProviders = (store) =>
  render(
    <Provider store={store}>
      <PaperProvider>
        <SettingsScreen />
      </PaperProvider>
    </Provider>,
  );

describe("SettingsScreen", () => {
  it("renders settings title", () => {
    renderWithProviders(createMockStore());
    expect(screen.getByText("Settings")).toBeTruthy();
  });

  it("shows user account info when logged in", () => {
    const store = createMockStore({
      name: "Jane Smith",
      email: "jane@example.com",
    });
    renderWithProviders(store);
    expect(screen.getByText("Jane Smith")).toBeTruthy();
    expect(screen.getByText("jane@example.com")).toBeTruthy();
  });

  it("does not show account section when no user", () => {
    renderWithProviders(createMockStore());
    expect(screen.queryByText("Account")).toBeNull();
  });

  it("renders theme options", () => {
    renderWithProviders(createMockStore());
    expect(screen.getByText("Light")).toBeTruthy();
    expect(screen.getByText("Dark")).toBeTruthy();
    expect(screen.getByText("System Default")).toBeTruthy();
  });

  it("renders notification toggles", () => {
    renderWithProviders(createMockStore());
    expect(screen.getByText("Trade Alerts")).toBeTruthy();
    expect(screen.getByText("Research Updates")).toBeTruthy();
    expect(screen.getByText("Price Alerts")).toBeTruthy();
  });

  it("renders sign out button", () => {
    renderWithProviders(createMockStore());
    expect(screen.getByText("Sign Out")).toBeTruthy();
  });

  it("renders reset to defaults button", () => {
    renderWithProviders(createMockStore());
    expect(screen.getByText("Reset to Defaults")).toBeTruthy();
  });
});
