import { StyleSheet, View } from "react-native";
import { Card, Text, useTheme } from "react-native-paper";

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
      marginBottom: 14,
      width: "48%",
      borderRadius: 16,
      backgroundColor: theme.colors.surface,
      elevation: 2,
    },
    cardContent: {
      alignItems: "flex-start",
      paddingHorizontal: 14,
      paddingVertical: 14,
    },
    iconRow: {
      flexDirection: "row",
      alignItems: "center",
      marginBottom: 10,
    },
    iconContainer: {
      width: 36,
      height: 36,
      borderRadius: 10,
      backgroundColor: theme.colors.primary + "1A",
      alignItems: "center",
      justifyContent: "center",
    },
    iconText: {
      fontSize: 18,
    },
    title: {
      fontSize: 11,
      fontWeight: "600",
      color: theme.colors.onSurfaceVariant,
      letterSpacing: 0.3,
      marginBottom: 4,
      textTransform: "uppercase",
    },
    value: {
      fontSize: 18,
      fontWeight: "800",
      color: theme.colors.onSurface,
      letterSpacing: -0.5,
    },
    change: {
      fontSize: 12,
      fontWeight: "600",
      marginTop: 3,
    },
  });

  const iconMap = {
    "chart-line": "📈",
    "trending-up": "💹",
    "chart-bell-curve-cumulative": "📊",
    robot: "🤖",
  };

  return (
    <Card
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
    </Card>
  );
}
