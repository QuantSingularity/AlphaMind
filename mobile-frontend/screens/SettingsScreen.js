import { Alert, ScrollView, StyleSheet, View } from "react-native";
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
    Alert.alert("Sign Out", "Are you sure you want to sign out?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Sign Out",
        onPress: () => dispatch(logoutUser()),
        style: "destructive",
      },
    ]);

  const handleResetSettings = () =>
    Alert.alert(
      "Reset Settings",
      "Are you sure you want to reset all settings to defaults?",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Reset",
          onPress: () => dispatch(resetSettings()),
          style: "destructive",
        },
      ],
    );

  const styles = StyleSheet.create({
    container: {
      flexGrow: 1,
      backgroundColor: theme.colors.background,
    },
    // Header — matches web page header style
    header: {
      backgroundColor: theme.colors.surface,
      paddingHorizontal: 16,
      paddingTop: 24,
      paddingBottom: 20,
      borderBottomWidth: 1,
      borderBottomColor: theme.colors.outlineVariant,
    },
    headerTitle: {
      fontSize: 28,
      fontWeight: "800",
      color: theme.colors.onBackground,
      letterSpacing: -0.5,
      marginBottom: 4,
    },
    headerAccent: { color: theme.colors.primary },
    headerSubtitle: {
      fontSize: 14,
      color: theme.colors.onSurfaceVariant,
    },
    // User card — matches web card with profile info
    userCard: {
      margin: 16,
      backgroundColor: theme.colors.surface,
      borderRadius: 8,
      borderWidth: 1,
      borderColor: theme.colors.outlineVariant,
      padding: 16,
      flexDirection: "row",
      alignItems: "center",
      shadowColor: "#000",
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.05,
      shadowRadius: 3,
      elevation: 2,
    },
    avatarCircle: {
      width: 44,
      height: 44,
      borderRadius: 22,
      backgroundColor: theme.colors.primary,
      alignItems: "center",
      justifyContent: "center",
      marginRight: 12,
    },
    avatarText: {
      fontSize: 18,
      fontWeight: "800",
      color: "#FFFFFF",
    },
    userInfo: { flex: 1 },
    userName: {
      fontSize: 15,
      fontWeight: "700",
      color: theme.colors.onSurface,
    },
    userEmail: {
      fontSize: 13,
      color: theme.colors.onSurfaceVariant,
      marginTop: 1,
    },
    // Section cards — matches web shadow rounded-lg
    sectionCard: {
      marginHorizontal: 16,
      marginBottom: 12,
      backgroundColor: theme.colors.surface,
      borderRadius: 8,
      borderWidth: 1,
      borderColor: theme.colors.outlineVariant,
      overflow: "hidden",
      shadowColor: "#000",
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.04,
      shadowRadius: 3,
      elevation: 1,
    },
    sectionHeader: {
      paddingHorizontal: 16,
      paddingTop: 14,
      paddingBottom: 4,
    },
    sectionTitle: {
      fontSize: 11,
      fontWeight: "700",
      color: theme.colors.onSurfaceVariant,
      textTransform: "uppercase",
      letterSpacing: 0.8,
    },
    radioGroupContainer: {
      paddingHorizontal: 16,
      paddingBottom: 8,
    },
    radioGroupLabel: {
      fontSize: 14,
      fontWeight: "600",
      color: theme.colors.onSurface,
      marginBottom: 4,
      marginTop: 8,
    },
    listItem: {
      paddingLeft: 0,
    },
    // Footer buttons
    buttonSection: {
      marginHorizontal: 16,
      marginTop: 8,
      marginBottom: 4,
      gap: 10,
    },
    resetButton: {
      borderRadius: 6,
      borderColor: theme.colors.outline,
    },
    resetButtonContent: { paddingVertical: 4 },
    logoutButton: {
      borderRadius: 6,
    },
    logoutButtonContent: { paddingVertical: 4 },
    versionText: {
      textAlign: "center",
      color: theme.colors.onSurfaceVariant,
      fontSize: 12,
      marginVertical: 20,
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
