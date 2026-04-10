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

  const handleThemeChange = (newTheme) => {
    dispatch(setTheme(newTheme));
  };

  const handleNotificationToggle = (key) => {
    dispatch(setNotifications({ [key]: !settings.notifications[key] }));
  };

  const handleCurrencyChange = (currency) => {
    dispatch(setDisplayPreferences({ currency }));
  };

  const handleLogout = () => {
    Alert.alert("Sign Out", "Are you sure you want to sign out?", [
      {
        text: "Cancel",
        style: "cancel",
      },
      {
        text: "Sign Out",
        onPress: () => dispatch(logoutUser()),
        style: "destructive",
      },
    ]);
  };

  const handleResetSettings = () => {
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
  };

  const styles = StyleSheet.create({
    container: {
      flexGrow: 1,
      backgroundColor: theme.colors.background,
    },
    headerSection: {
      padding: 20,
      paddingBottom: 8,
    },
    titleText: {
      fontSize: 24,
      fontWeight: "800",
      color: theme.colors.onBackground,
      marginBottom: 4,
    },
    subtitleText: {
      fontSize: 14,
      color: theme.colors.onSurfaceVariant,
    },
    sectionCard: {
      margin: 16,
      marginBottom: 0,
      borderRadius: 16,
      backgroundColor: theme.colors.surface,
      overflow: "hidden",
      elevation: 1,
    },
    radioGroupContainer: {
      paddingHorizontal: 16,
      paddingBottom: 8,
    },
    radioLabel: {
      fontSize: 12,
      fontWeight: "700",
      letterSpacing: 0.8,
      textTransform: "uppercase",
      color: theme.colors.onSurfaceVariant,
      marginTop: 12,
      marginBottom: 4,
      paddingHorizontal: 4,
    },
    buttonSection: {
      margin: 16,
      marginTop: 24,
      gap: 12,
    },
    logoutButton: {
      borderRadius: 12,
    },
    resetButton: {
      borderRadius: 12,
    },
    versionText: {
      textAlign: "center",
      color: theme.colors.outline,
      fontSize: 12,
      marginVertical: 16,
    },
  });

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.headerSection}>
        <Text style={styles.titleText}>Settings</Text>
        <Text style={styles.subtitleText}>Customize your experience</Text>
      </View>

      {user && (
        <View style={styles.sectionCard}>
          <List.Section title="Account">
            <List.Item
              title={user.name || "User"}
              description={user.email}
              left={(props) => (
                <List.Icon {...props} icon="account-circle-outline" />
              )}
            />
          </List.Section>
        </View>
      )}

      <View style={styles.sectionCard}>
        <List.Section title="Appearance">
          <View style={styles.radioGroupContainer}>
            <Text style={styles.radioLabel}>Theme</Text>
            <RadioButton.Group
              onValueChange={handleThemeChange}
              value={settings.theme}
            >
              <RadioButton.Item label="Light" value="light" />
              <RadioButton.Item label="Dark" value="dark" />
              <RadioButton.Item label="System Default" value="system" />
            </RadioButton.Group>
          </View>
        </List.Section>
      </View>

      <View style={styles.sectionCard}>
        <List.Section title="Notifications">
          <List.Item
            title="Trade Alerts"
            description="Get notified when trades are executed"
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
            right={() => (
              <Switch
                value={settings.notifications.researchUpdates}
                onValueChange={() =>
                  handleNotificationToggle("researchUpdates")
                }
                color={theme.colors.primary}
              />
            )}
          />
          <Divider />
          <List.Item
            title="Price Alerts"
            description="Alert on significant price movements"
            right={() => (
              <Switch
                value={settings.notifications.priceAlerts}
                onValueChange={() => handleNotificationToggle("priceAlerts")}
                color={theme.colors.primary}
              />
            )}
          />
        </List.Section>
      </View>

      <View style={styles.sectionCard}>
        <List.Section title="Display">
          <View style={styles.radioGroupContainer}>
            <Text style={styles.radioLabel}>Currency</Text>
            <RadioButton.Group
              onValueChange={handleCurrencyChange}
              value={settings.displayPreferences.currency}
            >
              <RadioButton.Item label="USD ($)" value="USD" />
              <RadioButton.Item label="EUR (€)" value="EUR" />
              <RadioButton.Item label="GBP (£)" value="GBP" />
            </RadioButton.Group>
          </View>
        </List.Section>
      </View>

      <View style={styles.buttonSection}>
        <Button
          mode="outlined"
          onPress={handleResetSettings}
          style={styles.resetButton}
        >
          Reset to Defaults
        </Button>

        <Button
          mode="contained"
          onPress={handleLogout}
          style={styles.logoutButton}
          buttonColor={theme.colors.error}
          textColor={theme.colors.onError}
        >
          Sign Out
        </Button>
      </View>

      <Text style={styles.versionText}>AlphaMind v1.0.0</Text>
    </ScrollView>
  );
}
