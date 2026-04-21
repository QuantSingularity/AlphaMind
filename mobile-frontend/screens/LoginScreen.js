import { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text as RNText,
  View,
} from "react-native";
import { Button, Text, TextInput, useTheme } from "react-native-paper";
import { useDispatch, useSelector } from "react-redux";
import { loginUser } from "../store/slices/authSlice";

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function LoginScreen({ navigation }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState("");

  const dispatch = useDispatch();
  const { loading } = useSelector((state) => state.auth);
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
    input: {
      marginBottom: 14,
      backgroundColor: theme.colors.surface,
    },
    primaryButton: {
      borderRadius: 6,
      marginTop: 4,
    },
    primaryButtonContent: {
      paddingVertical: 6,
    },
    errorText: {
      color: theme.colors.error || "#DC2626",
      fontSize: 13,
      marginTop: 8,
      textAlign: "center",
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
            <Text style={styles.appNameDark}>AlphaMind</Text>
          </View>
          <Text style={styles.subtitle}>Sign in to your trading dashboard</Text>
        </View>

        {/* Form card */}
        <View style={styles.formCard}>
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

          <Pressable
            onPress={handleLogin}
            disabled={loading || (!email && !password)}
          >
            <View
              accessible={true}
              accessibilityRole="button"
              accessibilityState={{
                disabled: loading || (!email && !password),
              }}
              style={[
                styles.primaryButton,
                {
                  backgroundColor: theme.colors.primary,
                  alignItems: "center",
                  justifyContent: "center",
                  paddingVertical: 14,
                  borderRadius: 6,
                  opacity: loading || (!email && !password) ? 0.5 : 1,
                },
              ]}
            >
              <RNText
                style={{ color: "#fff", fontWeight: "700", fontSize: 15 }}
              >
                Sign In
              </RNText>
            </View>
          </Pressable>

          {!!localError && <Text style={styles.errorText}>{localError}</Text>}

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
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
