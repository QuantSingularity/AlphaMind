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
    container: { flex: 1, backgroundColor: theme.colors.background },
    scrollContent: {
      flexGrow: 1,
      justifyContent: "center",
      padding: 28,
    },
    logoContainer: {
      alignItems: "center",
      marginBottom: 32,
    },
    logoCircle: {
      width: 60,
      height: 60,
      borderRadius: 30,
      backgroundColor: theme.colors.primary,
      alignItems: "center",
      justifyContent: "center",
      marginBottom: 14,
    },
    logoText: {
      color: theme.colors.onPrimary,
      fontSize: 24,
      fontWeight: "900",
    },
    appName: {
      fontSize: 24,
      fontWeight: "800",
      color: theme.colors.onBackground,
    },
    subtitle: {
      marginTop: 6,
      fontSize: 14,
      color: theme.colors.onSurfaceVariant,
      textAlign: "center",
    },
    input: { marginBottom: 4 },
    inputSpacing: { marginBottom: 12 },
    button: { marginTop: 12, borderRadius: 12 },
    buttonContent: { paddingVertical: 6 },
    dividerRow: {
      flexDirection: "row",
      alignItems: "center",
      marginVertical: 20,
    },
    dividerLine: {
      flex: 1,
      height: 1,
      backgroundColor: theme.colors.outline,
      opacity: 0.4,
    },
    dividerText: {
      marginHorizontal: 12,
      color: theme.colors.onSurfaceVariant,
      fontSize: 12,
    },
    linkButton: { marginTop: 4 },
  });

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      style={styles.container}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.logoContainer}>
          <View style={styles.logoCircle}>
            <Text style={styles.logoText}>α</Text>
          </View>
          <Text style={styles.appName}>Create Account</Text>
          <Text style={styles.subtitle}>Join AlphaMind to start trading</Text>
        </View>

        <TextInput
          label="Full Name"
          value={name}
          onChangeText={setName}
          mode="outlined"
          autoCapitalize="words"
          autoComplete="name"
          autoCorrect={false}
          style={styles.input}
          left={<TextInput.Icon icon="account-outline" />}
          testID="name-input"
        />
        <View style={styles.inputSpacing} />

        <TextInput
          label="Email"
          value={email}
          onChangeText={setEmail}
          mode="outlined"
          keyboardType="email-address"
          autoCapitalize="none"
          autoComplete="email"
          autoCorrect={false}
          style={styles.input}
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
          visible={password.length > 0 && password.length < MIN_PASSWORD_LENGTH}
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
          style={styles.button}
          contentStyle={styles.buttonContent}
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
          style={styles.linkButton}
          disabled={loading}
        >
          Already have an account? Sign In
        </Button>

        <Snackbar
          visible={!!displayError}
          onDismiss={handleDismissError}
          duration={4000}
          action={{
            label: "Dismiss",
            onPress: handleDismissError,
          }}
        >
          {displayError}
        </Snackbar>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
