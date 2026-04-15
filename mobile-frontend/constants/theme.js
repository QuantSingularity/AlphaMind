import { MD3DarkTheme, MD3LightTheme } from "react-native-paper";

// AlphaMind Web Design System Colors
// Primary: #2563EB (blue-600), Background: #F9FAFB (gray-50), Surface: #FFFFFF
export const lightTheme = {
  ...MD3LightTheme,
  colors: {
    ...MD3LightTheme.colors,
    primary: "#2563EB",
    primaryLight: "#DBEAFE",
    primaryDark: "#1D4ED8",
    secondary: "#6B7280",
    tertiary: "#10B981",
    error: "#DC2626",
    onError: "#FFFFFF",
    success: "#16A34A",
    warning: "#D97706",
    background: "#F9FAFB",
    surface: "#FFFFFF",
    surfaceVariant: "#F3F4F6",
    onPrimary: "#FFFFFF",
    onSecondary: "#FFFFFF",
    onBackground: "#111827",
    onSurface: "#111827",
    onSurfaceVariant: "#6B7280",
    outline: "#D1D5DB",
    outlineVariant: "#E5E7EB",
  },
};

export const darkTheme = {
  ...MD3DarkTheme,
  colors: {
    ...MD3DarkTheme.colors,
    primary: "#3B82F6",
    primaryLight: "#1E3A5F",
    primaryDark: "#60A5FA",
    secondary: "#9CA3AF",
    tertiary: "#34D399",
    error: "#F87171",
    onError: "#000000",
    success: "#4ADE80",
    warning: "#FCD34D",
    background: "#111827",
    surface: "#1F2937",
    surfaceVariant: "#374151",
    onPrimary: "#FFFFFF",
    onSecondary: "#FFFFFF",
    onBackground: "#F9FAFB",
    onSurface: "#F9FAFB",
    onSurfaceVariant: "#9CA3AF",
    outline: "#4B5563",
    outlineVariant: "#374151",
  },
};

export const getTheme = (isDark) => (isDark ? darkTheme : lightTheme);
