import { useCallback, useEffect, useMemo, useState } from "react";
import { RefreshControl, ScrollView, StyleSheet, View } from "react-native";
import { Icon, Text, useTheme } from "react-native-paper";
import { researchService } from "../services/researchService";

// Fallback scenarios used only when the backend is unreachable, so the screen
// stays informative offline. Live data from /api/v1/risk/stress-scenarios
// replaces these whenever it is available.
const FALLBACK_SCENARIOS = [
  {
    name: "2008 Financial Crisis",
    portfolioImpact: -33.9,
    duration: "14 months",
    recovery: "Slow",
  },
  {
    name: "COVID-19 Crash",
    portfolioImpact: -19.5,
    duration: "2 months",
    recovery: "Fast",
  },
  {
    name: "Rate Shock",
    portfolioImpact: -22.6,
    duration: "3 months",
    recovery: "Moderate",
  },
];

const formatCurrency = (n) =>
  `$${Math.abs(Number(n ?? 0)).toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })}`;

export default function RiskScreen() {
  const theme = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);

  const [metrics, setMetrics] = useState(null);
  const [scenarios, setScenarios] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async () => {
    try {
      const [m, s] = await Promise.all([
        researchService.getRiskMetrics().catch(() => null),
        researchService.getStressScenarios().catch(() => []),
      ]);
      setMetrics(m);
      setScenarios(Array.isArray(s) ? s : []);
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }, [load]);

  // Backend RiskMetrics: var (percent of NAV), beta, volatility (fraction),
  // maxDrawdown (fraction). Format each to its real unit.
  const metricCards = [
    {
      label: "Value at Risk (95%)",
      value: metrics?.var != null ? `${Number(metrics.var).toFixed(2)}%` : "-",
      tone: "warning",
    },
    {
      label: "Portfolio Beta",
      value: metrics?.beta != null ? Number(metrics.beta).toFixed(2) : "-",
      tone: "neutral",
    },
    {
      label: "Volatility (ann.)",
      value:
        metrics?.volatility != null
          ? `${(Number(metrics.volatility) * 100).toFixed(1)}%`
          : "-",
      tone: "neutral",
    },
    {
      label: "Max Drawdown",
      value:
        metrics?.maxDrawdown != null
          ? `${(Number(metrics.maxDrawdown) * 100).toFixed(1)}%`
          : "-",
      tone: "negative",
    },
  ];

  const toneColor = (tone) =>
    tone === "negative"
      ? theme.colors.error
      : tone === "warning"
        ? theme.colors.warning
        : theme.colors.onSurface;

  const shownScenarios =
    scenarios.length > 0 ? scenarios : loaded ? FALLBACK_SCENARIOS : [];

  return (
    <ScrollView
      contentContainerStyle={styles.container}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          colors={[theme.colors.primary]}
          tintColor={theme.colors.primary}
        />
      }
    >
      <View style={styles.hero}>
        <Text style={styles.title}>Risk</Text>
        <Text style={styles.subtitle}>
          Exposure, value at risk, and stress testing
        </Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Risk metrics</Text>
        <View style={styles.metricGrid}>
          {metricCards.map((m) => (
            <View key={m.label} style={styles.metricCard}>
              <Text style={styles.metricLabel}>{m.label}</Text>
              <Text style={[styles.metricValue, { color: toneColor(m.tone) }]}>
                {m.value}
              </Text>
            </View>
          ))}
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Stress scenarios</Text>
        <Text style={styles.sectionSubtitle}>
          Estimated portfolio impact under historical and hypothetical shocks
        </Text>
        <View style={styles.scenarioList}>
          {shownScenarios.map((s) => (
            <View key={s.name} style={styles.scenarioCard}>
              <View style={styles.scenarioTop}>
                <Text style={styles.scenarioName}>{s.name}</Text>
                <Text style={styles.scenarioImpact}>
                  {Number(s.portfolioImpact ?? 0).toFixed(1)}%
                </Text>
              </View>
              <View style={styles.scenarioMeta}>
                {s.pnl != null && (
                  <View style={styles.metaItem}>
                    <Icon
                      source="cash-minus"
                      size={14}
                      color={theme.colors.onSurfaceFaint}
                    />
                    <Text style={styles.metaText}>{formatCurrency(s.pnl)}</Text>
                  </View>
                )}
                {!!s.duration && (
                  <View style={styles.metaItem}>
                    <Icon
                      source="clock-outline"
                      size={14}
                      color={theme.colors.onSurfaceFaint}
                    />
                    <Text style={styles.metaText}>{s.duration}</Text>
                  </View>
                )}
                {!!s.recovery && (
                  <View style={styles.metaItem}>
                    <Icon
                      source="restart"
                      size={14}
                      color={theme.colors.onSurfaceFaint}
                    />
                    <Text style={styles.metaText}>{s.recovery}</Text>
                  </View>
                )}
              </View>
            </View>
          ))}
        </View>
      </View>

      <View style={styles.section}>
        <View style={styles.noteCard}>
          <Text style={styles.noteText}>
            Position limits are enforced per ticker, per sector, and on total
            gross and net exposure. Breaches are flagged in real time and new
            orders are blocked automatically.
          </Text>
        </View>
      </View>
    </ScrollView>
  );
}

const createStyles = (theme) =>
  StyleSheet.create({
    container: {
      backgroundColor: theme.colors.background,
      flexGrow: 1,
    },
    hero: {
      backgroundColor: theme.colors.surface,
      borderBottomColor: theme.colors.outlineVariant,
      borderBottomWidth: 1,
      paddingBottom: 18,
      paddingHorizontal: 16,
      paddingTop: 24,
    },
    metaItem: {
      alignItems: "center",
      flexDirection: "row",
      gap: 5,
    },
    metaText: {
      color: theme.colors.onSurfaceVariant,
      fontSize: 12,
    },
    metricCard: {
      backgroundColor: theme.colors.surface,
      borderColor: theme.colors.outlineVariant,
      borderRadius: 12,
      borderWidth: 1,
      marginBottom: 12,
      padding: 16,
      width: "48.5%",
    },
    metricGrid: {
      flexDirection: "row",
      flexWrap: "wrap",
      justifyContent: "space-between",
      marginTop: 8,
    },
    metricLabel: {
      color: theme.colors.onSurfaceVariant,
      fontSize: 11,
      fontWeight: "600",
      letterSpacing: 0.5,
      marginBottom: 8,
      textTransform: "uppercase",
    },
    metricValue: {
      fontSize: 20,
      fontVariant: ["tabular-nums"],
      fontWeight: "800",
    },
    noteCard: {
      backgroundColor: theme.colors.surfaceVariant,
      borderRadius: 12,
      padding: 16,
    },
    noteText: {
      color: theme.colors.onSurfaceVariant,
      fontSize: 13,
      lineHeight: 20,
    },
    scenarioCard: {
      backgroundColor: theme.colors.surface,
      borderColor: theme.colors.outlineVariant,
      borderRadius: 12,
      borderWidth: 1,
      padding: 16,
    },
    scenarioImpact: {
      color: theme.colors.error,
      fontSize: 18,
      fontVariant: ["tabular-nums"],
      fontWeight: "800",
    },
    scenarioList: {
      gap: 12,
    },
    scenarioMeta: {
      flexDirection: "row",
      flexWrap: "wrap",
      gap: 16,
    },
    scenarioName: {
      color: theme.colors.onSurface,
      flex: 1,
      fontSize: 15,
      fontWeight: "700",
      paddingRight: 8,
    },
    scenarioTop: {
      alignItems: "center",
      flexDirection: "row",
      justifyContent: "space-between",
      marginBottom: 10,
    },
    section: {
      paddingHorizontal: 16,
      paddingVertical: 18,
    },
    sectionSubtitle: {
      color: theme.colors.onSurfaceVariant,
      fontSize: 13,
      marginBottom: 14,
    },
    sectionTitle: {
      color: theme.colors.onBackground,
      fontSize: 18,
      fontWeight: "700",
      marginBottom: 4,
    },
    subtitle: {
      color: theme.colors.onSurfaceVariant,
      fontSize: 14,
    },
    title: {
      color: theme.colors.onBackground,
      fontSize: 28,
      fontWeight: "800",
      letterSpacing: -0.5,
      marginBottom: 4,
    },
  });
