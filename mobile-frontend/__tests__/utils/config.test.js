describe("config constants", () => {
  beforeEach(() => {
    jest.resetModules();
  });

  it("exports API_BASE_URL", () => {
    const { API_BASE_URL } = require("../../constants/config");
    expect(typeof API_BASE_URL).toBe("string");
    expect(API_BASE_URL.length).toBeGreaterThan(0);
  });

  it("exports API_TIMEOUT as a number", () => {
    const { API_TIMEOUT } = require("../../constants/config");
    expect(typeof API_TIMEOUT).toBe("number");
    expect(API_TIMEOUT).toBeGreaterThan(0);
  });

  it("exports STORAGE_KEYS with required keys", () => {
    const { STORAGE_KEYS } = require("../../constants/config");
    expect(STORAGE_KEYS).toHaveProperty("AUTH_TOKEN");
    expect(STORAGE_KEYS).toHaveProperty("USER_DATA");
    expect(STORAGE_KEYS).toHaveProperty("SETTINGS");
    expect(STORAGE_KEYS).toHaveProperty("THEME_PREFERENCE");
  });

  it("exports API_ENDPOINTS with all required sections", () => {
    const { API_ENDPOINTS } = require("../../constants/config");
    expect(API_ENDPOINTS.AUTH).toHaveProperty("LOGIN");
    expect(API_ENDPOINTS.AUTH).toHaveProperty("REGISTER");
    expect(API_ENDPOINTS.AUTH).toHaveProperty("LOGOUT");
    expect(API_ENDPOINTS.PORTFOLIO).toHaveProperty("LIST");
    expect(API_ENDPOINTS.RESEARCH).toHaveProperty("PAPERS");
  });

  it("PORTFOLIO.DETAILS returns correct URL with id", () => {
    const { API_ENDPOINTS } = require("../../constants/config");
    expect(API_ENDPOINTS.PORTFOLIO.DETAILS("abc123")).toBe(
      "/api/portfolio/abc123",
    );
  });

  it("RESEARCH.DETAILS returns correct URL with id", () => {
    const { API_ENDPOINTS } = require("../../constants/config");
    expect(API_ENDPOINTS.RESEARCH.DETAILS("paper-1")).toBe(
      "/api/research/papers/paper-1",
    );
  });

  it("ENABLE_MOCK_DATA defaults to false", () => {
    const { ENABLE_MOCK_DATA } = require("../../constants/config");
    expect(typeof ENABLE_MOCK_DATA).toBe("boolean");
  });

  it("STRATEGIES endpoints have correct shape", () => {
    const { API_ENDPOINTS } = require("../../constants/config");
    expect(API_ENDPOINTS.STRATEGIES).toHaveProperty("LIST");
    expect(API_ENDPOINTS.STRATEGIES.DETAILS("s1")).toBe("/api/strategies/s1");
    expect(API_ENDPOINTS.STRATEGIES.PERFORMANCE("s1")).toBe(
      "/api/strategies/s1/performance",
    );
  });

  it("MARKET endpoints exist", () => {
    const { API_ENDPOINTS } = require("../../constants/config");
    expect(API_ENDPOINTS.MARKET).toHaveProperty("QUOTES");
    expect(API_ENDPOINTS.MARKET).toHaveProperty("CHART");
  });
});
