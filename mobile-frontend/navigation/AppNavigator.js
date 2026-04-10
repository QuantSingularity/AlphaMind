import { useState } from "react";
import { BottomNavigation, useTheme } from "react-native-paper";
import DocumentationScreen from "../screens/DocumentationScreen";
import FeaturesScreen from "../screens/FeaturesScreen";
import HomeScreen from "../screens/HomeScreen";
import ResearchScreen from "../screens/ResearchScreen";
import SettingsScreen from "../screens/SettingsScreen";

const HomeRoute = () => <HomeScreen />;
const FeaturesRoute = () => <FeaturesScreen />;
const DocsRoute = () => <DocumentationScreen />;
const ResearchRoute = () => <ResearchScreen />;
const SettingsRoute = () => <SettingsScreen />;

const routes = [
  {
    key: "home",
    title: "Home",
    focusedIcon: "home",
    unfocusedIcon: "home-outline",
  },
  {
    key: "features",
    title: "Features",
    focusedIcon: "star",
    unfocusedIcon: "star-outline",
  },
  {
    key: "docs",
    title: "Docs",
    focusedIcon: "file-document",
    unfocusedIcon: "file-document-outline",
  },
  {
    key: "research",
    title: "Research",
    focusedIcon: "flask",
    unfocusedIcon: "flask-outline",
  },
  {
    key: "settings",
    title: "Settings",
    focusedIcon: "cog",
    unfocusedIcon: "cog-outline",
  },
];

const renderScene = BottomNavigation.SceneMap({
  home: HomeRoute,
  features: FeaturesRoute,
  docs: DocsRoute,
  research: ResearchRoute,
  settings: SettingsRoute,
});

export default function AppNavigator() {
  const [index, setIndex] = useState(0);
  const theme = useTheme();

  return (
    <BottomNavigation
      navigationState={{ index, routes }}
      onIndexChange={setIndex}
      renderScene={renderScene}
      activeColor={theme.colors.primary}
      barStyle={{ backgroundColor: theme.colors.surface }}
    />
  );
}
