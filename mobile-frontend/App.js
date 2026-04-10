import { NavigationContainer } from "@react-navigation/native";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";
import { useColorScheme } from "react-native";
import { Provider as PaperProvider } from "react-native-paper";
import { SafeAreaProvider } from "react-native-safe-area-context";
import {
  Provider as ReduxProvider,
  useDispatch,
  useSelector,
} from "react-redux";
import LoadingSpinner from "./components/LoadingSpinner";
import { darkTheme, lightTheme } from "./constants/theme";
import AppNavigator from "./navigation/AppNavigator";
import AuthNavigator from "./navigation/AuthNavigator";
import store from "./store";
import { checkAuth } from "./store/slices/authSlice";
import { loadSavedSettings } from "./store/slices/settingsSlice";

function AppContent() {
  const dispatch = useDispatch();
  const { isAuthenticated, loading } = useSelector((state) => state.auth);
  const { theme: themePreference } = useSelector((state) => state.settings);
  const systemColorScheme = useColorScheme();

  useEffect(() => {
    dispatch(checkAuth());
    dispatch(loadSavedSettings());
  }, [dispatch]);

  const effectiveTheme =
    themePreference === "system"
      ? systemColorScheme === "dark"
        ? "dark"
        : "light"
      : themePreference;

  const theme = effectiveTheme === "dark" ? darkTheme : lightTheme;

  if (loading) {
    return (
      <PaperProvider theme={theme}>
        <LoadingSpinner message="Loading AlphaMind..." />
      </PaperProvider>
    );
  }

  return (
    <PaperProvider theme={theme}>
      <StatusBar style={effectiveTheme === "dark" ? "light" : "dark"} />
      <NavigationContainer>
        {isAuthenticated ? <AppNavigator /> : <AuthNavigator />}
      </NavigationContainer>
    </PaperProvider>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <ReduxProvider store={store}>
        <AppContent />
      </ReduxProvider>
    </SafeAreaProvider>
  );
}
