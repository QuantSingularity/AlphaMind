import AsyncStorage from "@react-native-async-storage/async-storage";
import { render, screen, waitFor } from "@testing-library/react-native";
import App from "../../App";
import api from "../../services/api";

jest.mock("../../services/api", () => ({
  __esModule: true,
  default: {
    post: jest.fn(),
    get: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
  },
}));

jest.mock("expo-constants", () => ({
  default: {
    expoConfig: {
      extra: { apiBaseUrl: "http://localhost:5000" },
    },
  },
}));

jest.mock("react-native-safe-area-context", () => {
  const React = require("react");
  const insets = { top: 0, bottom: 0, left: 0, right: 0 };
  const SafeAreaInsetsContext = React.createContext(insets);
  return {
    SafeAreaProvider: ({ children }) =>
      React.createElement(
        SafeAreaInsetsContext.Provider,
        { value: insets },
        children,
      ),
    SafeAreaView: ({ children, style }) =>
      React.createElement("View", { style }, children),
    useSafeAreaInsets: () => insets,
    SafeAreaConsumer: SafeAreaInsetsContext.Consumer,
    SafeAreaInsetsContext,
    initialWindowMetrics: {
      insets,
      frame: { x: 0, y: 0, width: 390, height: 844 },
    },
  };
});

describe("App integration", () => {
  beforeEach(async () => {
    jest.clearAllMocks();
    await AsyncStorage.clear();
  });

  it("renders auth screen when not authenticated", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText("AlphaMind")).toBeTruthy();
    });
  }, 15000);

  it("shows sign in button on login screen", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText("Sign In")).toBeTruthy();
    });
  }, 15000);

  it("shows create account link on login screen", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText("Create an Account")).toBeTruthy();
    });
  }, 15000);
});

describe("Auth flow", () => {
  beforeEach(async () => {
    jest.clearAllMocks();
    await AsyncStorage.clear();
    // Portfolio API returns null data so HomeScreen renders without spinner/error
    api.get.mockResolvedValue({ data: null });
  });

  it("shows dashboard when authenticated", async () => {
    const testUser = { id: 1, name: "Test User", email: "test@example.com" };
    await AsyncStorage.setItem("@alphamind/auth_token", "test-token");
    await AsyncStorage.setItem(
      "@alphamind/user_data",
      JSON.stringify(testUser),
    );

    render(<App />);

    await waitFor(
      () => {
        expect(screen.getByText("Dashboard")).toBeTruthy();
      },
      { timeout: 10000 },
    );
  }, 15000);

  it("shows welcome message with user name when authenticated", async () => {
    const testUser = { id: 1, name: "Jane Doe", email: "jane@example.com" };
    await AsyncStorage.setItem("@alphamind/auth_token", "test-token");
    await AsyncStorage.setItem(
      "@alphamind/user_data",
      JSON.stringify(testUser),
    );

    render(<App />);

    await waitFor(
      () => {
        expect(screen.getByText("Jane Doe")).toBeTruthy();
      },
      { timeout: 10000 },
    );
  }, 15000);
});
