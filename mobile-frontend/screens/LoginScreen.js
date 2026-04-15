import { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  View,
} from "react-native";
import {
  Button,
  Snackbar,
  Text,
  TextInput,
  useTheme,
} from "react-native-paper";
import { useDispatch, useSelector } from "react-redux";
import { clearError, loginUser } from "../store/slices/authSlice";

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function LoginScreen({ navigation }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState("");

  const dispatch = useDispatch();
  const { loading, error } = useSelector((state) => state.auth);
  const theme = useTheme();

  const handleLogin = async () => {
    setLocalError("");
    if (!email.trim()) {
      setLocalError("Email is required");
      return;
    }
    if (!EMAIL_REGEX.test(email.trim())) {
      setLocalError("Please enter a valid email address");
      return;
    }
    if (!password) {
      setLocalError("Password is required");
      return;
    }
    dispatch(loginUser({ email: email.trim(), password }));
  };

  const handleDismissError = () => {
    dispatch(clearError());
    setLocalError("");
  };

  const displayError = localError || error;

  const styles = StyleSheet.create({
    outerContainer: {
      flex: 1,
      backgroundColor: theme.colors.background,
    },
    scrollContent: {
      flexGrow: 1,
      justifyContent: "center",
      padding: 24,
    },
    // Brand block — matches web navbar logo "AlphaMind"
    brandBlock: {
      alignItems: "center",
      marginBottom: 40,
    },
    logoCircle: {
      width: 64,
      height: 64,
      borderRadius: 32,
      backgroundColor: theme.colors.primary,
      alignItems: "center",
      justifyContent: "center",
      marginBottom: 16,
      shadowColor: theme.colors.primary,
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.3,
      shadowRadius: 8,
      elevation: 6,
    },
    logoLetter: {
      color: "#FFFFFF",
      fontSize: 26,
      fontWeight: "900",
      letterSpacing: 1,
    },
    appNameRow: {
      flexDirection: "row",
      alignItems: "center",
      marginBottom: 6,
    },
    appNameDark: {
      fontSize: 26,
      fontWeight: "800",
      color: theme.colors.onBackground,
      letterSpacing: -0.3,
    },
    appNameBlue: {
      fontSize: 26,
      fontWeight: "800",
      color: theme.colors.primary,
      letterSpacing: -0.3,
    },
    subtitle: {
      fontSize: 14,
      color: theme.colors.onSurfaceVariant,
      textAlign: "center",
    },
    // Form card — matches web card style
    formCard: {
      backgroundColor: theme.colors.surface,
      borderRadius: 8,
      borderWidth: 1,
      borderColor: theme.colors.outlineVariant,
      padding: 24,
      shadowColor: "#000",
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.05,
      shadowRadius: 4,
      elevation: 2,
      marginBottom: 16,
    },
    formLabel: {
      fontSize: 11,
      fontWeight: "700",
      color: theme.colors.onSurfaceVariant,
      textTransform: "uppercase",
      letterSpacing: 0.8,
      marginBottom: 16,
    },
    input: {
      marginBottom: 14,
      backgroundColor: theme.colors.surface,
    },
    // Primary button — matches web bg-blue-600 rounded-md
    primaryButton: {
      borderRadius: 6,
      marginTop: 4,
    },
    primaryButtonContent: {
      paddingVertical: 6,
    },
    dividerRow: {
      flexDirection: "row",
      alignItems: "center",
      marginVertical: 18,
    },
    dividerLine: {
      flex: 1,
      height: 1,
      backgroundColor: theme.colors.outlineVariant,
    },
    dividerText: {
      marginHorizontal: 12,
      color: theme.colors.onSurfaceVariant,
      fontSize: 12,
    },
    outlineButton: {
      borderRadius: 6,
      borderColor: theme.colors.primary,
    },
    outlineButtonContent: {
      paddingVertical: 6,
    },
  });

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      style={styles.outerContainer}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        {/* Brand block */}
        <View style={styles.brandBlock}>
          <View style={styles.logoCircle}>
            <Text style={styles.logoLetter}>α</Text>
          </View>
          <View style={styles.appNameRow}>
            <Text style={styles.appNameDark}>Alpha</Text>
            <Text style={styles.appNameBlue}>Mind</Text>
          </View>
          <Text style={styles.subtitle}>Sign in to your trading dashboard</Text>
        </View>

        {/* Form card */}
        <View style={styles.formCard}>
          <Text style={styles.formLabel}>Sign In</Text>

          <TextInput
            label="Email address"
            value={email}
            onChangeText={setEmail}
            mode="outlined"
            keyboardType="email-address"
            autoCapitalize="none"
            autoComplete="email"
            autoCorrect={false}
            style={styles.input}
            outlineColor={theme.colors.outlineVariant}
            activeOutlineColor={theme.colors.primary}
            left={<TextInput.Icon icon="email-outline" />}
            testID="email-input"
          />

          <TextInput
            label="Password"
            value={password}
            onChangeText={setPassword}
            mode="outlined"
            secureTextEntry={!showPassword}
            autoCapitalize="none"
            autoComplete="current-password"
            style={styles.input}
            outlineColor={theme.colors.outlineVariant}
            activeOutlineColor={theme.colors.primary}
            left={<TextInput.Icon icon="lock-outline" />}
            right={
              <TextInput.Icon
                icon={showPassword ? "eye-off-outline" : "eye-outline"}
                onPress={() => setShowPassword(!showPassword)}
              />
            }
            testID="password-input"
          />

          <Button
            mode="contained"
            onPress={handleLogin}
            loading={loading}
            disabled={loading || !email || !password}
            style={styles.primaryButton}
            contentStyle={styles.primaryButtonContent}
            buttonColor={theme.colors.primary}
          >
            Get Started
          </Button>

          <View style={styles.dividerRow}>
            <View style={styles.dividerLine} />
            <Text style={styles.dividerText}>or</Text>
            <View style={styles.dividerLine} />
          </View>

          <Button
            mode="outlined"
            onPress={() => navigation.navigate("Register")}
            style={styles.outlineButton}
            contentStyle={styles.outlineButtonContent}
            textColor={theme.colors.primary}
            disabled={loading}
          >
            Create an Account
          </Button>
        </View>

        <Snackbar
          visible={!!displayError}
          onDismiss={handleDismissError}
          duration={4000}
          action={{ label: "Dismiss", onPress: handleDismissError }}
        >
          {displayError}
        </Snackbar>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
