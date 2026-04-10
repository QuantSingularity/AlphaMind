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
    container: { flex: 1, backgroundColor: theme.colors.background },
    scrollContent: {
      flexGrow: 1,
      justifyContent: "center",
      padding: 28,
    },
    logoContainer: {
      alignItems: "center",
      marginBottom: 40,
    },
    logoCircle: {
      width: 72,
      height: 72,
      borderRadius: 36,
      backgroundColor: theme.colors.primary,
      alignItems: "center",
      justifyContent: "center",
      marginBottom: 16,
    },
    logoText: {
      color: theme.colors.onPrimary,
      fontSize: 28,
      fontWeight: "900",
      letterSpacing: 1,
    },
    appName: {
      fontSize: 26,
      fontWeight: "800",
      color: theme.colors.onBackground,
      letterSpacing: 0.5,
    },
    subtitle: {
      marginTop: 6,
      fontSize: 14,
      color: theme.colors.onSurfaceVariant,
      textAlign: "center",
    },
    input: { marginBottom: 16 },
    button: { marginTop: 8, borderRadius: 12 },
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
          <Text style={styles.appName}>AlphaMind</Text>
          <Text style={styles.subtitle}>Sign in to your trading dashboard</Text>
        </View>

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

        <TextInput
          label="Password"
          value={password}
          onChangeText={setPassword}
          mode="outlined"
          secureTextEntry={!showPassword}
          autoCapitalize="none"
          autoComplete="current-password"
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

        <Button
          mode="contained"
          onPress={handleLogin}
          loading={loading}
          disabled={loading || !email || !password}
          style={styles.button}
          contentStyle={styles.buttonContent}
        >
          Sign In
        </Button>

        <View style={styles.dividerRow}>
          <View style={styles.dividerLine} />
          <Text style={styles.dividerText}>or</Text>
          <View style={styles.dividerLine} />
        </View>

        <Button
          mode="outlined"
          onPress={() => navigation.navigate("Register")}
          style={styles.linkButton}
          disabled={loading}
        >
          Create an Account
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
