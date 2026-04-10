import { StyleSheet, View } from "react-native";
import { ActivityIndicator, Text, useTheme } from "react-native-paper";

export default function LoadingSpinner({
  message = "Loading...",
  size = "large",
  fullScreen = true,
}) {
  const theme = useTheme();

  const styles = StyleSheet.create({
    container: {
      alignItems: "center",
      flex: 1,
      justifyContent: "center",
      backgroundColor: theme.colors.background,
    },
    inline: {
      alignItems: "center",
      justifyContent: "center",
      paddingVertical: 20,
    },
    message: {
      marginTop: 16,
      fontSize: 14,
      color: theme.colors.onSurfaceVariant,
    },
  });

  return (
    <View
      style={fullScreen ? styles.container : styles.inline}
      accessible
      accessibilityRole="progressbar"
      accessibilityLabel={message}
    >
      <ActivityIndicator size={size} color={theme.colors.primary} />
      {!!message && <Text style={styles.message}>{message}</Text>}
    </View>
  );
}
