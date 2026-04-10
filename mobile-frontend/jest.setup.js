import "@testing-library/react-native/extend-expect";

jest.mock("@react-native-async-storage/async-storage", () =>
  require("@react-native-async-storage/async-storage/jest/async-storage-mock"),
);

jest.mock("react-native-vector-icons/MaterialCommunityIcons", () => "Icon");

jest.mock("expo-status-bar", () => ({
  StatusBar: "StatusBar",
}));

jest.mock("expo-constants", () => ({
  default: {
    expoConfig: {
      extra: {
        apiBaseUrl: "http://localhost:5000",
      },
      version: "1.0.0",
    },
  },
}));

jest.mock("react-native-svg", () => {
  const React = require("react");
  const MockSvg = ({ children }) => React.createElement("Svg", {}, children);
  return {
    Svg: MockSvg,
    Circle: "Circle",
    G: "G",
    Path: "Path",
    Rect: "Rect",
    Line: "Line",
    Text: "Text",
    TSpan: "TSpan",
    Defs: "Defs",
    LinearGradient: "LinearGradient",
    Stop: "Stop",
  };
});

jest.mock("react-native-safe-area-context", () => {
  const React = require("react");
  return {
    SafeAreaProvider: ({ children }) =>
      React.createElement("View", {}, children),
    SafeAreaView: ({ children }) => React.createElement("View", {}, children),
    useSafeAreaInsets: () => ({ top: 0, bottom: 0, left: 0, right: 0 }),
    SafeAreaConsumer: ({ children }) =>
      children({ top: 0, bottom: 0, left: 0, right: 0 }),
  };
});

jest.mock("react-native-paper", () => {
  const RealModule = jest.requireActual("react-native-paper");
  return RealModule;
});

jest.mock(
  "../../store/settingsListener",
  () => ({
    settingsListenerMiddleware: {
      middleware: () => (next) => (action) => next(action),
      startListening: jest.fn(),
    },
  }),
  { virtual: true },
);

global.console = {
  ...console,
  warn: jest.fn(),
  error: jest.fn(),
};
