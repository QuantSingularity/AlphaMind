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
  HelperText,
  Snackbar,
  Text,
  TextInput,
  useTheme,
} from "react-native-paper";
import { useDispatch, useSelector } from "react-redux";
import { clearError, registerUser } from "../store/slices/authSlice";

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_PASSWORD_LENGTH = 8;

export default function RegisterScreen({ navigation }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [localError, setLocalError] = useState("");

  const dispatch = useDispatch();
  const { loading, error } = useSelector((state) => state.auth);
  const theme = useTheme();

  const handleRegister = async () => {
    setLocalError("");
    if (!name.trim()) {
      setLocalError("Full name is required");
      return;
    }
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
    if (password.length < MIN_PASSWORD_LENGTH) {
      setLocalError(
        `Password must be at least ${MIN_PASSWORD_LENGTH} characters`,
      );
      return;
    }
    if (password !== confirmPassword) {
      setLocalError("Passwords do not match");
      return;
    }
    dispatch(
      registerUser({ name: name.trim(), email: email.trim(), password }),
    );
  };

  const handleDismissError = () => {
    dispatch(clearError());
    setLocalError("");
  };

  const displayError = localError || error;
  const passwordsMatch =
    confirmPassword.length > 0 && password !== confirmPassword;
  const isFormValid =
    name.trim() && email.trim() && password && confirmPassword;

  const styles = StyleSheet.create({
    outerContainer: { flex: 1, backgroundColor: theme.colors.background },
    scrollContent: { flexGrow: 1, justifyContent: "center", padding: 24 },
    brandBlock: { alignItems: "center", marginBottom: 32 },
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
    appNameRow: { flexDirection: "row", alignItems: "center", marginBottom: 6 },
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
    input: { marginBottom: 4, backgroundColor: theme.colors.surface },
    inputSpacing: { marginBottom: 10 },
    primaryButton: { borderRadius: 6, marginTop: 8 },
    primaryButtonContent: { paddingVertical: 6 },
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
    outlineButton: { borderRadius: 6, borderColor: theme.colors.primary },
    outlineButtonContent: { paddingVertical: 6 },
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
        <View style={styles.brandBlock}>
          <View style={styles.logoCircle}>
            <Text style={styles.logoLetter}>α</Text>
          </View>
          <View style={styles.appNameRow}>
            <Text style={styles.appNameDark}>Alpha</Text>
            <Text style={styles.appNameBlue}>Mind</Text>
          </View>
          <Text style={styles.subtitle}>Join AlphaMind to start trading</Text>
        </View>

        <View style={styles.formCard}>
          <Text style={styles.formLabel}>Create Account</Text>

          <TextInput
            label="Full Name"
            value={name}
            onChangeText={setName}
            mode="outlined"
            autoCapitalize="words"
            autoComplete="name"
            autoCorrect={false}
            style={styles.input}
            outlineColor={theme.colors.outlineVariant}
            activeOutlineColor={theme.colors.primary}
            left={<TextInput.Icon icon="account-outline" />}
            testID="name-input"
          />
          <View style={styles.inputSpacing} />

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
          <View style={styles.inputSpacing} />

          <TextInput
            label="Password"
            value={password}
            onChangeText={setPassword}
            mode="outlined"
            secureTextEntry={!showPassword}
            autoCapitalize="none"
            autoComplete="new-password"
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
          <HelperText
            type="info"
            visible={
              password.length > 0 && password.length < MIN_PASSWORD_LENGTH
            }
          >
            Password must be at least {MIN_PASSWORD_LENGTH} characters
          </HelperText>

          <TextInput
            label="Confirm Password"
            value={confirmPassword}
            onChangeText={setConfirmPassword}
            mode="outlined"
            secureTextEntry={!showConfirmPassword}
            autoCapitalize="none"
            autoComplete="new-password"
            style={styles.input}
            error={passwordsMatch}
            outlineColor={theme.colors.outlineVariant}
            activeOutlineColor={theme.colors.primary}
            left={<TextInput.Icon icon="lock-check-outline" />}
            right={
              <TextInput.Icon
                icon={showConfirmPassword ? "eye-off-outline" : "eye-outline"}
                onPress={() => setShowConfirmPassword(!showConfirmPassword)}
              />
            }
            testID="confirm-password-input"
          />
          <HelperText type="error" visible={passwordsMatch}>
            Passwords do not match
          </HelperText>

          <Button
            mode="contained"
            onPress={handleRegister}
            loading={loading}
            disabled={loading || !isFormValid}
            style={styles.primaryButton}
            contentStyle={styles.primaryButtonContent}
            buttonColor={theme.colors.primary}
          >
            Create Account
          </Button>

          <View style={styles.dividerRow}>
            <View style={styles.dividerLine} />
            <Text style={styles.dividerText}>or</Text>
            <View style={styles.dividerLine} />
          </View>

          <Button
            mode="outlined"
            onPress={() => navigation.navigate("Login")}
            style={styles.outlineButton}
            contentStyle={styles.outlineButtonContent}
            textColor={theme.colors.primary}
            disabled={loading}
          >
            Already have an account? Sign In
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
