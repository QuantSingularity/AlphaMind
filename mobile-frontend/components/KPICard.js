import { StyleSheet, View } from "react-native";
import { Icon, Text, useTheme } from "react-native-paper";

export default function KPICard({
  title,
  value,
  change,
  changeColor,
  icon,
  isLoading,
}) {
  const theme = useTheme();

  const styles = StyleSheet.create({
    card: {
      marginBottom: 12,
      width: "48.5%",
      borderRadius: 8,
      backgroundColor: theme.colors.surface,
      borderWidth: 1,
      borderColor: theme.colors.outlineVariant,
      // shadow matching web: shadow rounded-lg
      shadowColor: "#000",
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.05,
      shadowRadius: 3,
      elevation: 2,
      overflow: "hidden",
    },
    cardContent: {
      padding: 16,
    },
    change: {
      fontSize: 12,
      fontWeight: "600",
      marginTop: 4,
    },
    iconContainer: {
      alignItems: "center",
      backgroundColor: theme.colors.primaryLight || "#DBEAFE",
      borderRadius: 6,
      height: 32,
      justifyContent: "center",
      width: 32,
    },
    iconRow: {
      alignItems: "center",
      flexDirection: "row",
      marginBottom: 10,
    },
    title: {
      color: theme.colors.onSurfaceVariant,
      fontSize: 11,
      fontWeight: "500",
      letterSpacing: 0.5,
      marginBottom: 4,
      textTransform: "uppercase",
    },
    value: {
      color: theme.colors.onSurface,
      fontSize: 20,
      fontWeight: "700",
      letterSpacing: -0.3,
    },
  });

  return (
    <View
      style={styles.card}
      accessible
      accessibilityLabel={`${title}: ${isLoading ? "loading" : value}`}
    >
      <View style={styles.cardContent}>
        {icon && (
          <View style={styles.iconRow}>
            <View style={styles.iconContainer}>
              <Icon source={icon} size={18} color={theme.colors.primary} />
            </View>
          </View>
        )}
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.value}>{isLoading ? "-" : value}</Text>
        {!!change && (
          <Text
            style={[
              styles.change,
              { color: changeColor || theme.colors.onSurface },
            ]}
          >
            {change}
          </Text>
        )}
      </View>
    </View>
  );
}
