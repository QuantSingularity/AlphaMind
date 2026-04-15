import { StyleSheet, View } from "react-native";
import { Text, useTheme } from "react-native-paper";

export default function KPICard({
  title,
  value,
  change,
  changeColor,
  icon,
  isLoading,
}) {
  const theme = useTheme();

  const iconMap = {
    "chart-line": "📈",
    "trending-up": "💹",
    "chart-bell-curve-cumulative": "📊",
    robot: "🤖",
  };

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
    iconRow: {
      flexDirection: "row",
      alignItems: "center",
      marginBottom: 10,
    },
    iconContainer: {
      width: 32,
      height: 32,
      borderRadius: 6,
      backgroundColor: theme.colors.primaryLight || "#DBEAFE",
      alignItems: "center",
      justifyContent: "center",
    },
    iconText: {
      fontSize: 16,
    },
    title: {
      fontSize: 11,
      fontWeight: "500",
      color: theme.colors.onSurfaceVariant,
      letterSpacing: 0.5,
      marginBottom: 4,
      textTransform: "uppercase",
    },
    value: {
      fontSize: 20,
      fontWeight: "700",
      color: theme.colors.onSurface,
      letterSpacing: -0.3,
    },
    change: {
      fontSize: 12,
      fontWeight: "600",
      marginTop: 4,
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
              <Text style={styles.iconText}>{iconMap[icon] || "📌"}</Text>
            </View>
          </View>
        )}
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.value}>{isLoading ? "—" : value}</Text>
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
