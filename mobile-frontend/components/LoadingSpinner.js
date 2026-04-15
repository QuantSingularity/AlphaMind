import { ActivityIndicator, StyleSheet, View } from "react-native";
import { Text, useTheme } from "react-native-paper";

export default function LoadingSpinner({ message = "Loading..." }) {
  const theme = useTheme();

  const styles = StyleSheet.create({
    container: {
      flex: 1,
      alignItems: "center",
      justifyContent: "center",
      backgroundColor: theme.colors.background,
      padding: 24,
    },
    spinnerWrapper: {
      width: 48,
      height: 48,
      alignItems: "center",
      justifyContent: "center",
      marginBottom: 16,
    },
    message: {
      fontSize: 14,
      color: theme.colors.onSurfaceVariant,
      textAlign: "center",
    },
  });

  return (
    <View style={styles.container}>
      <View style={styles.spinnerWrapper}>
        <ActivityIndicator size="large" color={theme.colors.primary} />
      </View>
      <Text style={styles.message}>{message}</Text>
    </View>
  );
}
