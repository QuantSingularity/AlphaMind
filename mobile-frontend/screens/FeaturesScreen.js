import { ScrollView, StyleSheet, View } from "react-native";
import { Text, useTheme } from "react-native-paper";

const features = [
  {
    key: "altdata",
    icon: "🛰️",
    title: "Alternative Data Integration",
    tag: "Data",
    tagColor: "#2563EB",
    description:
      "Process satellite imagery, SEC filings, sentiment analysis, and social media data for comprehensive market insights.",
    items: [
      "Satellite imagery processing",
      "SEC 8K real-time monitoring",
      "Earnings call NLP sentiment analysis",
      "Social media sentiment tracking",
    ],
  },
  {
    key: "quant",
    icon: "📊",
    title: "Quantitative Research",
    tag: "Analytics",
    tagColor: "#2563EB",
    description:
      "Advanced ML models and quantitative techniques for alpha generation and strategy development.",
    items: [
      "Machine learning factor models",
      "Regime switching detection",
      "Exotic derivatives pricing",
      "Advanced portfolio optimization",
    ],
  },
  {
    key: "exec",
    icon: "⚡",
    title: "Execution Infrastructure",
    tag: "Speed",
    tagColor: "#DC2626",
    description:
      "High-performance execution engine with smart order routing and adaptive algorithms.",
    items: [
      "Microsecond latency arbitrage",
      "Hawkes process liquidity forecasting",
      "Smart order routing",
      "Adaptive execution algorithms",
    ],
  },
  {
    key: "risk",
    icon: "🛡️",
    title: "Risk Management",
    tag: "Protection",
    tagColor: "#D97706",
    description:
      "Comprehensive risk assessment and mitigation framework with real-time monitoring.",
    items: [
      "Bayesian VaR with regime adjustments",
      "Counterparty credit risk (CVA/DVA)",
      "Extreme scenario stress testing",
      "Real-time risk monitoring",
    ],
  },
  {
    key: "ai",
    icon: "🧠",
    title: "AI/ML Core",
    tag: "Intelligence",
    tagColor: "#7C3AED",
    description:
      "Cutting-edge artificial intelligence and machine learning to gain a competitive edge in financial markets.",
    items: [
      "Temporal Fusion Transformers",
      "Reinforcement Learning optimization",
      "Generative market simulation",
      "Attention-based time series analysis",
    ],
  },
  {
    key: "portfolio",
    icon: "💼",
    title: "Portfolio Construction",
    tag: "Optimization",
    tagColor: "#059669",
    description:
      "Build and rebalance diversified portfolios using modern portfolio theory and constraints.",
    items: [
      "Mean-variance optimization",
      "Factor exposure management",
      "Constraint-based rebalancing",
      "Correlation-aware allocation",
    ],
  },
];

export default function FeaturesScreen() {
  const theme = useTheme();

  const styles = StyleSheet.create({
    container: {
      flexGrow: 1,
      backgroundColor: theme.colors.background,
    },
    // Header matches web hero section
    header: {
      backgroundColor: theme.colors.surface,
      paddingHorizontal: 16,
      paddingTop: 24,
      paddingBottom: 20,
      borderBottomWidth: 1,
      borderBottomColor: theme.colors.outlineVariant,
    },
    headerTitle: {
      fontSize: 28,
      fontWeight: "800",
      color: theme.colors.onBackground,
      letterSpacing: -0.5,
      marginBottom: 4,
    },
    headerAccent: {
      color: theme.colors.primary,
    },
    headerSubtitle: {
      fontSize: 14,
      color: theme.colors.onSurfaceVariant,
      lineHeight: 20,
    },
    // Grid section
    gridSection: {
      padding: 16,
      paddingTop: 20,
    },
    sectionLabel: {
      fontSize: 11,
      fontWeight: "700",
      color: theme.colors.onSurfaceVariant,
      letterSpacing: 1,
      textTransform: "uppercase",
      marginBottom: 14,
    },
    // Feature card — matches web bg-white rounded-lg shadow-lg p-6
    card: {
      backgroundColor: theme.colors.surface,
      borderRadius: 8,
      borderWidth: 1,
      borderColor: theme.colors.outlineVariant,
      padding: 20,
      marginBottom: 12,
      shadowColor: "#000",
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.07,
      shadowRadius: 6,
      elevation: 3,
    },
    cardTop: {
      flexDirection: "row",
      justifyContent: "space-between",
      alignItems: "flex-start",
      marginBottom: 10,
    },
    iconText: {
      fontSize: 32,
      marginBottom: 6,
    },
    tag: {
      paddingHorizontal: 10,
      paddingVertical: 3,
      borderRadius: 20,
      alignSelf: "flex-start",
    },
    tagText: {
      fontSize: 11,
      fontWeight: "700",
    },
    cardTitle: {
      fontSize: 16,
      fontWeight: "700",
      color: theme.colors.onSurface,
      marginBottom: 8,
      lineHeight: 22,
    },
    cardDescription: {
      fontSize: 13,
      color: theme.colors.onSurfaceVariant,
      lineHeight: 20,
      marginBottom: 14,
    },
    divider: {
      height: 1,
      backgroundColor: theme.colors.outlineVariant,
      marginBottom: 12,
    },
    itemRow: {
      flexDirection: "row",
      alignItems: "flex-start",
      marginBottom: 6,
    },
    itemCheck: {
      fontSize: 13,
      color: theme.colors.primary,
      marginRight: 8,
      marginTop: 1,
      fontWeight: "700",
    },
    itemText: {
      fontSize: 13,
      color: theme.colors.onSurfaceVariant,
      flex: 1,
      lineHeight: 18,
    },
  });

  return (
    <ScrollView contentContainerStyle={styles.container}>
      {/* Header — matches web "Key Features" section heading */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>
          Key <Text style={styles.headerAccent}>Features</Text>
        </Text>
        <Text style={styles.headerSubtitle}>
          Comprehensive tools for institutional-grade quantitative trading
        </Text>
      </View>

      <View style={styles.gridSection}>
        <Text style={styles.sectionLabel}>Core Capabilities</Text>

        {features.map((feature) => (
          <View key={feature.key} style={styles.card}>
            <Text style={styles.iconText}>{feature.icon}</Text>

            <View style={styles.cardTop}>
              <Text style={styles.cardTitle}>{feature.title}</Text>
              <View
                style={[
                  styles.tag,
                  { backgroundColor: feature.tagColor + "18" },
                ]}
              >
                <Text style={[styles.tagText, { color: feature.tagColor }]}>
                  {feature.tag}
                </Text>
              </View>
            </View>

            <Text style={styles.cardDescription}>{feature.description}</Text>

            <View style={styles.divider} />

            {feature.items.map((item) => (
              <View key={item} style={styles.itemRow}>
                <Text style={styles.itemCheck}>✓</Text>
                <Text style={styles.itemText}>{item}</Text>
              </View>
            ))}
          </View>
        ))}
      </View>
    </ScrollView>
  );
}
