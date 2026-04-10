import { StyleSheet, View } from "react-native";
import { Button, Text, useTheme } from "react-native-paper";

export default function ErrorMessage({
  message,
  onRetry,
  title = "Something went wrong",
}) {
  const theme = useTheme();

  const styles = StyleSheet.create({
    container: {
      alignItems: "center",
      flex: 1,
      justifyContent: "center",
      padding: 32,
      backgroundColor: theme.colors.background,
    },
    iconText: {
      fontSize: 56,
      marginBottom: 16,
    },
    title: {
      fontSize: 18,
      fontWeight: "700",
      color: theme.colors.error,
      textAlign: "center",
      marginBottom: 8,
    },
    message: {
      fontSize: 14,
      color: theme.colors.onSurfaceVariant,
      textAlign: "center",
      lineHeight: 21,
    },
    button: {
      marginTop: 24,
      borderRadius: 12,
    },
  });

  return (
    <View style={styles.container} accessible accessibilityRole="alert">
      <Text style={styles.iconText}>⚠️</Text>
      <Text style={styles.title}>{title}</Text>
      {!!message && <Text style={styles.message}>{message}</Text>}
      {onRetry && (
        <Button mode="contained" onPress={onRetry} style={styles.button}>
          Try Again
        </Button>
      )}
    </View>
  );
}
