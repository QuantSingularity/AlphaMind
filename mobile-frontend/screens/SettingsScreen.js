import { Alert, Platform, ScrollView, StyleSheet, View } from "react-native";
import {
  Button,
  Divider,
  List,
  RadioButton,
  Switch,
  Text,
  useTheme,
} from "react-native-paper";
import { useDispatch, useSelector } from "react-redux";
import { logoutUser } from "../store/slices/authSlice";
import {
  resetSettings,
  setDisplayPreferences,
  setNotifications,
  setTheme,
} from "../store/slices/settingsSlice";

// Alert.alert is a no-op on React Native Web, so confirmation dialogs (and the
// actions behind them, like Sign Out) never fire in the browser. Use the
// browser's confirm there and the native Alert on devices.
function confirmAction({ title, message, confirmLabel, onConfirm }) {
  if (Platform.OS === "web") {
    const globalScope =
      typeof globalThis !== "undefined" ? globalThis : undefined;
    const ok =
      globalScope && typeof globalScope.confirm === "function"
        ? globalScope.confirm(`${title}\n\n${message}`)
        : true;
    if (ok) onConfirm();
    return;
  }
  Alert.alert(title, message, [
    { text: "Cancel", style: "cancel" },
    { text: confirmLabel, onPress: onConfirm, style: "destructive" },
  ]);
}

export default function SettingsScreen() {
  const theme = useTheme();
  const dispatch = useDispatch();
  const settings = useSelector((state) => state.settings);
  const { user } = useSelector((state) => state.auth);

  const handleThemeChange = (newTheme) => dispatch(setTheme(newTheme));
  const handleNotificationToggle = (key) =>
    dispatch(setNotifications({ [key]: !settings.notifications[key] }));
  const handleCurrencyChange = (currency) =>
    dispatch(setDisplayPreferences({ currency }));

  const handleLogout = () =>
    confirmAction({
      title: "Sign Out",
      message: "Are you sure you want to sign out?",
      confirmLabel: "Sign Out",
      onConfirm: () => dispatch(logoutUser()),
    });

  const handleResetSettings = () =>
    confirmAction({
      title: "Reset Settings",
      message: "Are you sure you want to reset all settings to defaults?",
      confirmLabel: "Reset",
      onConfirm: () => dispatch(resetSettings()),
    });

  const styles = StyleSheet.create({
    container: {
      backgroundColor: theme.colors.background,
      flexGrow: 1,
    },
    // Header - matches web page header style
    header: {
      backgroundColor: theme.colors.surface,
      borderBottomColor: theme.colors.outlineVariant,
      borderBottomWidth: 1,
      paddingBottom: 20,
      paddingHorizontal: 16,
      paddingTop: 24,
    },
    headerTitle: {
      color: theme.colors.onBackground,
      fontSize: 28,
      fontWeight: "800",
      letterSpacing: -0.5,
      marginBottom: 4,
    },
    headerAccent: { color: theme.colors.primary },
    headerSubtitle: {
      color: theme.colors.onSurfaceVariant,
      fontSize: 14,
    },
    // User card - matches web card with profile info
    userCard: {
      alignItems: "center",
      backgroundColor: theme.colors.surface,
      borderColor: theme.colors.outlineVariant,
      borderRadius: 8,
      borderWidth: 1,
      elevation: 2,
      flexDirection: "row",
      margin: 16,
      padding: 16,
      shadowColor: "#000",
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.05,
      shadowRadius: 3,
    },
    avatarCircle: {
      alignItems: "center",
      backgroundColor: theme.colors.primary,
      borderRadius: 22,
      height: 44,
      justifyContent: "center",
      marginRight: 12,
      width: 44,
    },
    avatarText: {
      color: "#FFFFFF",
      fontSize: 18,
      fontWeight: "800",
    },
    userInfo: { flex: 1 },
    userName: {
      color: theme.colors.onSurface,
      fontSize: 15,
      fontWeight: "700",
    },
    userEmail: {
      color: theme.colors.onSurfaceVariant,
      fontSize: 13,
      marginTop: 1,
    },
    // Section cards - matches web shadow rounded-lg
    sectionCard: {
      backgroundColor: theme.colors.surface,
      borderColor: theme.colors.outlineVariant,
      borderRadius: 8,
      borderWidth: 1,
      elevation: 1,
      marginBottom: 12,
      marginHorizontal: 16,
      overflow: "hidden",
      shadowColor: "#000",
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.04,
      shadowRadius: 3,
    },
    sectionHeader: {
      paddingBottom: 4,
      paddingHorizontal: 16,
      paddingTop: 14,
    },
    sectionTitle: {
      color: theme.colors.onSurfaceVariant,
      fontSize: 11,
      fontWeight: "700",
      letterSpacing: 0.8,
      textTransform: "uppercase",
    },
    radioGroupContainer: {
      paddingBottom: 8,
      paddingHorizontal: 16,
    },
    radioGroupLabel: {
      color: theme.colors.onSurface,
      fontSize: 14,
      fontWeight: "600",
      marginBottom: 4,
      marginTop: 8,
    },
    listItem: {
      paddingLeft: 0,
    },
    // Footer buttons
    buttonSection: {
      gap: 10,
      marginBottom: 4,
      marginHorizontal: 16,
      marginTop: 8,
    },
    resetButton: {
      borderColor: theme.colors.outline,
      borderRadius: 6,
    },
    resetButtonContent: { paddingVertical: 4 },
    logoutButton: {
      borderRadius: 6,
    },
    logoutButtonContent: { paddingVertical: 4 },
    versionText: {
      color: theme.colors.onSurfaceVariant,
      fontSize: 12,
      marginVertical: 20,
      textAlign: "center",
    },
  });

  const userInitial = user?.name
    ? user.name.charAt(0).toUpperCase()
    : user?.email?.charAt(0).toUpperCase() || "A";

  return (
    <ScrollView contentContainerStyle={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>
          <Text style={styles.headerAccent}>Settings</Text>
        </Text>
        <Text style={styles.headerSubtitle}>
          Manage your account and preferences
        </Text>
      </View>

      {/* User card */}
      {user && (
        <View style={styles.userCard}>
          <View style={styles.avatarCircle}>
            <Text style={styles.avatarText}>{userInitial}</Text>
          </View>
          <View style={styles.userInfo}>
            <Text style={styles.userName}>{user.name || "AlphaMind User"}</Text>
            <Text style={styles.userEmail}>{user.email}</Text>
          </View>
        </View>
      )}

      {/* Appearance */}
      <View style={styles.sectionCard}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Appearance</Text>
        </View>
        <View style={styles.radioGroupContainer}>
          <Text style={styles.radioGroupLabel}>Theme</Text>
          <RadioButton.Group
            onValueChange={handleThemeChange}
            value={settings.theme}
          >
            <RadioButton.Item
              label="Light"
              value="light"
              color={theme.colors.primary}
            />
            <RadioButton.Item
              label="Dark"
              value="dark"
              color={theme.colors.primary}
            />
            <RadioButton.Item
              label="System Default"
              value="system"
              color={theme.colors.primary}
            />
          </RadioButton.Group>
        </View>
      </View>

      {/* Notifications */}
      <View style={styles.sectionCard}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Notifications</Text>
        </View>
        <List.Item
          title="Trade Alerts"
          description="Get notified when trades are executed"
          style={styles.listItem}
          right={() => (
            <Switch
              value={settings.notifications.tradeAlerts}
              onValueChange={() => handleNotificationToggle("tradeAlerts")}
              color={theme.colors.primary}
            />
          )}
        />
        <Divider />
        <List.Item
          title="Research Updates"
          description="Receive new research paper notifications"
          style={styles.listItem}
          right={() => (
            <Switch
              value={settings.notifications.researchUpdates}
              onValueChange={() => handleNotificationToggle("researchUpdates")}
              color={theme.colors.primary}
            />
          )}
        />
        <Divider />
        <List.Item
          title="Price Alerts"
          description="Alert on significant price movements"
          style={styles.listItem}
          right={() => (
            <Switch
              value={settings.notifications.priceAlerts}
              onValueChange={() => handleNotificationToggle("priceAlerts")}
              color={theme.colors.primary}
            />
          )}
        />
      </View>

      {/* Display */}
      <View style={styles.sectionCard}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Display</Text>
        </View>
        <View style={styles.radioGroupContainer}>
          <Text style={styles.radioGroupLabel}>Currency</Text>
          <RadioButton.Group
            onValueChange={handleCurrencyChange}
            value={settings.displayPreferences.currency}
          >
            <RadioButton.Item
              label="USD ($)"
              value="USD"
              color={theme.colors.primary}
            />
            <RadioButton.Item
              label="EUR (€)"
              value="EUR"
              color={theme.colors.primary}
            />
            <RadioButton.Item
              label="GBP (£)"
              value="GBP"
              color={theme.colors.primary}
            />
          </RadioButton.Group>
        </View>
      </View>

      {/* Actions */}
      <View style={styles.buttonSection}>
        <Button
          mode="outlined"
          onPress={handleResetSettings}
          style={styles.resetButton}
          contentStyle={styles.resetButtonContent}
          textColor={theme.colors.onSurface}
        >
          Reset to Defaults
        </Button>
        <Button
          mode="contained"
          onPress={handleLogout}
          style={styles.logoutButton}
          contentStyle={styles.logoutButtonContent}
          buttonColor="#DC2626"
          textColor="#FFFFFF"
        >
          Sign Out
        </Button>
      </View>

      <Text style={styles.versionText}>AlphaMind v1.0.0</Text>
    </ScrollView>
  );
}
