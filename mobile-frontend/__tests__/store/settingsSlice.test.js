import settingsReducer, {
  loadSavedSettings,
  resetSettings,
  setDisplayPreferences,
  setNotifications,
  setTheme,
} from "../../store/slices/settingsSlice";

describe("settingsSlice", () => {
  const initialState = {
    theme: "system",
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
  };

  it("should return initial state", () => {
    expect(settingsReducer(undefined, { type: "unknown" })).toEqual(
      initialState,
    );
  });

  it("should handle setTheme", () => {
    const state = settingsReducer(initialState, setTheme("dark"));
    expect(state.theme).toBe("dark");
  });

  it("should handle setTheme to light", () => {
    const state = settingsReducer(initialState, setTheme("light"));
    expect(state.theme).toBe("light");
  });

  it("should handle setNotifications - partial update", () => {
    const state = settingsReducer(
      initialState,
      setNotifications({ tradeAlerts: false }),
    );
    expect(state.notifications.tradeAlerts).toBe(false);
    expect(state.notifications.researchUpdates).toBe(true);
    expect(state.notifications.priceAlerts).toBe(true);
  });

  it("should handle setDisplayPreferences - partial update", () => {
    const state = settingsReducer(
      initialState,
      setDisplayPreferences({ currency: "EUR" }),
    );
    expect(state.displayPreferences.currency).toBe("EUR");
    expect(state.displayPreferences.decimalPlaces).toBe(2);
    expect(state.displayPreferences.chartType).toBe("line");
  });

  it("should handle resetSettings", () => {
    const modified = {
      ...initialState,
      theme: "dark",
      notifications: {
        tradeAlerts: false,
        researchUpdates: false,
        priceAlerts: false,
      },
    };
    const state = settingsReducer(modified, resetSettings());
    expect(state).toEqual(initialState);
  });

  it("should apply saved settings on loadSavedSettings.fulfilled", () => {
    const saved = {
      theme: "dark",
      notifications: {
        tradeAlerts: false,
        researchUpdates: true,
        priceAlerts: true,
      },
    };
    const state = settingsReducer(initialState, {
      type: loadSavedSettings.fulfilled.type,
      payload: saved,
    });
    expect(state.theme).toBe("dark");
    expect(state.notifications.tradeAlerts).toBe(false);
  });

  it("should not change state when loadSavedSettings.fulfilled payload is null", () => {
    const state = settingsReducer(initialState, {
      type: loadSavedSettings.fulfilled.type,
      payload: null,
    });
    expect(state).toEqual(initialState);
  });
});
