import { StyleSheet, View } from "react-native";
import { Button, Text, useTheme } from "react-native-paper";

export default function ErrorMessage({
  title = "Something went wrong",
  message,
  onRetry,
}) {
  const theme = useTheme();

  const styles = StyleSheet.create({
    container: {
      flex: 1,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: theme.colors.background,
      padding: 24,
    },
    errorBox: {
      backgroundColor: theme.colors.surface,
      borderRadius: 8,
      borderWidth: 1,
      borderColor: "#FCA5A5",
      padding: 20,
      maxWidth: 360,
      width: "100%",
      alignItems: "center",
      shadowColor: "#000",
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.05,
      shadowRadius: 3,
      elevation: 2,
    },
    icon: {
      fontSize: 28,
      marginBottom: 12,
    },
    title: {
      fontSize: 16,
      fontWeight: "700",
      color: "#DC2626",
      marginBottom: 8,
      textAlign: "center",
    },
    message: {
      fontSize: 13,
      color: theme.colors.onSurfaceVariant,
      textAlign: "center",
      lineHeight: 20,
      marginBottom: 16,
    },
    retryButton: {
      borderRadius: 6,
    },
    retryButtonContent: {
      paddingVertical: 2,
      paddingHorizontal: 8,
    },
  });

  return (
    <View style={styles.container} accessible={true} accessibilityRole="alert">
      <View style={styles.errorBox}>
        <Text style={styles.icon}>⚠️</Text>
        <Text style={styles.title}>{title}</Text>
        {message && <Text style={styles.message}>{message}</Text>}
        {onRetry && (
          <Button
            mode="contained"
            onPress={onRetry}
            style={styles.retryButton}
            contentStyle={styles.retryButtonContent}
            buttonColor={theme.colors.primary}
          >
            Try Again
          </Button>
        )}
      </View>
    </View>
  );
}
