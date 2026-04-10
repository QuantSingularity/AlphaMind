import { MD3DarkTheme, MD3LightTheme } from "react-native-paper";

export const lightTheme = {
  ...MD3LightTheme,
  colors: {
    ...MD3LightTheme.colors,
    primary: "#6200EE",
    secondary: "#03DAC6",
    tertiary: "#018786",
    error: "#B00020",
    onError: "#FFFFFF",
    success: "#4CAF50",
    warning: "#FF9800",
    background: "#F6F6F6",
    surface: "#FFFFFF",
    surfaceVariant: "#F0EAF8",
    onPrimary: "#FFFFFF",
    onSecondary: "#000000",
    onBackground: "#1A1A1A",
    onSurface: "#1A1A1A",
    onSurfaceVariant: "#5A5A72",
    outline: "#9E9EAF",
  },
};

export const darkTheme = {
  ...MD3DarkTheme,
  colors: {
    ...MD3DarkTheme.colors,
    primary: "#BB86FC",
    secondary: "#03DAC6",
    tertiary: "#03DAC6",
    error: "#CF6679",
    onError: "#000000",
    success: "#81C784",
    warning: "#FFB74D",
    background: "#0E0E16",
    surface: "#1A1A2E",
    surfaceVariant: "#252540",
    onPrimary: "#000000",
    onSecondary: "#000000",
    onBackground: "#E8E8F0",
    onSurface: "#E8E8F0",
    onSurfaceVariant: "#A0A0C0",
    outline: "#5A5A7A",
  },
};

export const getTheme = (isDark) => (isDark ? darkTheme : lightTheme);
