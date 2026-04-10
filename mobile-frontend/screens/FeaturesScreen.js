import { ScrollView, StyleSheet, View } from "react-native";
import { Card, Chip, Text, useTheme } from "react-native-paper";

export default function FeaturesScreen() {
  const theme = useTheme();

  const features = [
    {
      key: "ai",
      icon: "brain",
      title: "AI/ML Core",
      tag: "Intelligence",
      tagColor: "#7C4DFF",
      description:
        "Leverage advanced machine learning models for predictive analytics and strategy generation.",
    },
    {
      key: "quant",
      icon: "chart-bar",
      title: "Quantitative Research",
      tag: "Analytics",
      tagColor: "#0091EA",
      description:
        "Access powerful tools for backtesting, factor analysis, and portfolio optimization.",
    },
    {
      key: "altdata",
      icon: "satellite-uplink",
      title: "Alternative Data Integration",
      tag: "Data",
      tagColor: "#00BFA5",
      description:
        "Incorporate diverse datasets like satellite imagery, social media sentiment, and more.",
    },
    {
      key: "risk",
      icon: "shield-check",
      title: "Risk Management",
      tag: "Protection",
      tagColor: "#FF6D00",
      description:
        "Utilize sophisticated risk models and real-time monitoring to protect capital.",
    },
    {
      key: "exec",
      icon: "lightning-bolt",
      title: "Execution Infrastructure",
      tag: "Speed",
      tagColor: "#D50000",
      description:
        "Connect seamlessly with brokers for low-latency order execution and management.",
    },
    {
      key: "portfolio",
      icon: "briefcase-outline",
      title: "Portfolio Construction",
      tag: "Optimization",
      tagColor: "#2962FF",
      description:
        "Build and rebalance diversified portfolios using modern portfolio theory and constraints.",
    },
  ];

  const styles = StyleSheet.create({
    container: {
      flexGrow: 1,
      padding: 20,
      backgroundColor: theme.colors.background,
    },
    headerSection: {
      marginBottom: 28,
      paddingTop: 8,
    },
    titleText: {
      fontSize: 24,
      fontWeight: "800",
      color: theme.colors.onBackground,
      marginBottom: 6,
    },
    subtitleText: {
      fontSize: 14,
      color: theme.colors.onSurfaceVariant,
      lineHeight: 20,
    },
    card: {
      marginBottom: 14,
      borderRadius: 16,
      backgroundColor: theme.colors.surface,
      elevation: 2,
    },
    cardContent: {
      padding: 16,
    },
    cardHeader: {
      flexDirection: "row",
      justifyContent: "space-between",
      alignItems: "flex-start",
      marginBottom: 10,
    },
    cardTitle: {
      fontSize: 16,
      fontWeight: "700",
      color: theme.colors.onSurface,
      flex: 1,
      marginRight: 8,
    },
    cardDescription: {
      fontSize: 13,
      color: theme.colors.onSurfaceVariant,
      lineHeight: 20,
    },
    chip: {
      height: 26,
    },
    chipText: {
      fontSize: 10,
      fontWeight: "700",
    },
  });

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.headerSection}>
        <Text style={styles.titleText}>Features</Text>
        <Text style={styles.subtitleText}>
          Discover the core capabilities powering the AlphaMind platform.
        </Text>
      </View>

      {features.map((feature) => (
        <Card key={feature.key} style={styles.card}>
          <View style={styles.cardContent}>
            <View style={styles.cardHeader}>
              <Text style={styles.cardTitle}>{feature.title}</Text>
              <Chip
                style={[
                  styles.chip,
                  { backgroundColor: feature.tagColor + "22" },
                ]}
                textStyle={[styles.chipText, { color: feature.tagColor }]}
                compact
              >
                {feature.tag}
              </Chip>
            </View>
            <Text style={styles.cardDescription}>{feature.description}</Text>
          </View>
        </Card>
      ))}
    </ScrollView>
  );
}
