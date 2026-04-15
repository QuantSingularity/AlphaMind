import { useCallback, useEffect, useMemo, useState } from "react";
import { RefreshControl, ScrollView, StyleSheet, View } from "react-native";
import { Text, useTheme } from "react-native-paper";
import { useDispatch, useSelector } from "react-redux";
import ErrorMessage from "../components/ErrorMessage";
import KPICard from "../components/KPICard";
import LoadingSpinner from "../components/LoadingSpinner";
import { fetchPortfolio } from "../store/slices/portfolioSlice";

// Performance metrics matching web Home.tsx
const performanceMetrics = [
  {
    strategy: "TFT Alpha",
    sharpeRatio: 2.1,
    maxDD: "12%",
    profitFactor: 3.4,
    winRate: "62%",
  },
  {
    strategy: "RL Portfolio",
    sharpeRatio: 1.8,
    maxDD: "15%",
    profitFactor: 2.9,
    winRate: "58%",
  },
  {
    strategy: "Hybrid Approach",
    sharpeRatio: 2.4,
    maxDD: "9%",
    profitFactor: 4.1,
    winRate: "65%",
  },
  {
    strategy: "Sentiment-Enhanced",
    sharpeRatio: 2.2,
    maxDD: "11%",
    profitFactor: 3.7,
    winRate: "63%",
  },
];

export default function HomeScreen() {
  const theme = useTheme();
  const dispatch = useDispatch();

  const { data, loading, error } = useSelector((state) => state.portfolio);
  const { user } = useSelector((state) => state.auth);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    dispatch(fetchPortfolio());
  }, [dispatch]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await dispatch(fetchPortfolio());
    setRefreshing(false);
  }, [dispatch]);

  const kpiData = useMemo(() => {
    if (!data) {
      return [
        {
          title: "Portfolio Value",
          value: "$0.00",
          change: "0.0%",
          changeColor: theme.colors.onSurfaceVariant,
          icon: "chart-line",
        },
        {
          title: "Daily P&L",
          value: "$0.00",
          change: "0.0%",
          changeColor: theme.colors.onSurfaceVariant,
          icon: "trending-up",
        },
        {
          title: "Sharpe Ratio",
          value: "0.00",
          change: "",
          changeColor: theme.colors.primary,
          icon: "chart-bell-curve-cumulative",
        },
        {
          title: "Active Strategies",
          value: "0",
          change: "",
          changeColor: theme.colors.primary,
          icon: "robot",
        },
      ];
    }

    const portfolioValue = `$${(data.value ?? 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    const dailyPnLNum = data.dailyPnL ?? 0;
    const dailyPnL = `${dailyPnLNum >= 0 ? "+" : ""}$${Math.abs(dailyPnLNum).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    const dailyPnLPercent = data.dailyPnLPercent ?? 0;
    const dailyPnLChange = `${dailyPnLPercent >= 0 ? "+" : ""}${dailyPnLPercent.toFixed(2)}%`;
    const changeColor =
      dailyPnLPercent >= 0 ? theme.colors.success : theme.colors.error;

    return [
      {
        title: "Portfolio Value",
        value: portfolioValue,
        change: dailyPnLChange,
        changeColor,
        icon: "chart-line",
      },
      {
        title: "Daily P&L",
        value: dailyPnL,
        change: dailyPnLChange,
        changeColor,
        icon: "trending-up",
      },
      {
        title: "Sharpe Ratio",
        value: (data.sharpeRatio ?? 0).toFixed(2),
        change: "",
        changeColor: theme.colors.primary,
        icon: "chart-bell-curve-cumulative",
      },
      {
        title: "Active Strategies",
        value: String(data.activeStrategies ?? 0),
        change: "",
        changeColor: theme.colors.primary,
        icon: "robot",
      },
    ];
  }, [data, theme.colors]);

  const styles = useMemo(
    () =>
      StyleSheet.create({
        container: {
          backgroundColor: theme.colors.background,
          flexGrow: 1,
        },
        // Hero section matching web: gradient hero with blue accent
        heroSection: {
          backgroundColor: theme.colors.surface,
          paddingHorizontal: 16,
          paddingTop: 24,
          paddingBottom: 20,
          borderBottomWidth: 1,
          borderBottomColor: theme.colors.outlineVariant,
        },
        greetingText: {
          fontSize: 13,
          color: theme.colors.onSurfaceVariant,
          marginBottom: 4,
        },
        titleText: {
          fontSize: 28,
          fontWeight: "800",
          color: theme.colors.onBackground,
          marginBottom: 4,
          letterSpacing: -0.5,
        },
        titleAccent: {
          color: theme.colors.primary,
        },
        subtitleText: {
          fontSize: 14,
          color: theme.colors.onSurfaceVariant,
          lineHeight: 20,
        },
        // Section containers
        section: {
          paddingHorizontal: 16,
          paddingVertical: 20,
        },
        sectionAlt: {
          paddingHorizontal: 16,
          paddingVertical: 20,
          backgroundColor: theme.colors.surfaceVariant,
        },
        sectionHeader: {
          marginBottom: 16,
        },
        sectionTitle: {
          fontSize: 20,
          fontWeight: "700",
          color: theme.colors.onBackground,
          marginBottom: 4,
        },
        sectionSubtitle: {
          fontSize: 13,
          color: theme.colors.onSurfaceVariant,
        },
        // KPI grid matching web: grid-cols-2
        kpiContainer: {
          flexDirection: "row",
          flexWrap: "wrap",
          justifyContent: "space-between",
        },
        // Performance table matching web table design
        tableContainer: {
          backgroundColor: theme.colors.surface,
          borderRadius: 8,
          borderWidth: 1,
          borderColor: theme.colors.outlineVariant,
          overflow: "hidden",
          shadowColor: "#000",
          shadowOffset: { width: 0, height: 1 },
          shadowOpacity: 0.05,
          shadowRadius: 3,
          elevation: 2,
        },
        tableHeader: {
          flexDirection: "row",
          backgroundColor: theme.colors.surfaceVariant,
          paddingHorizontal: 12,
          paddingVertical: 10,
          borderBottomWidth: 1,
          borderBottomColor: theme.colors.outlineVariant,
        },
        tableHeaderCell: {
          fontSize: 10,
          fontWeight: "600",
          color: theme.colors.onSurfaceVariant,
          textTransform: "uppercase",
          letterSpacing: 0.5,
        },
        tableRow: {
          flexDirection: "row",
          paddingHorizontal: 12,
          paddingVertical: 12,
          borderBottomWidth: 1,
          borderBottomColor: theme.colors.outlineVariant,
          alignItems: "center",
        },
        tableRowLast: {
          borderBottomWidth: 0,
        },
        tableCellStrategy: {
          fontSize: 13,
          fontWeight: "600",
          color: theme.colors.onSurface,
        },
        tableCell: {
          fontSize: 13,
          color: theme.colors.onSurfaceVariant,
        },
        col1: { flex: 2.2 },
        col2: { flex: 1.2 },
        col3: { flex: 1.2 },
        col4: { flex: 1.4 },
        col5: { flex: 1.2 },
        // Info hint card
        hintCard: {
          backgroundColor: theme.colors.surface,
          borderRadius: 8,
          borderWidth: 1,
          borderColor: theme.colors.outlineVariant,
          padding: 14,
          marginTop: 4,
        },
        hintText: {
          color: theme.colors.onSurfaceVariant,
          fontSize: 12,
          textAlign: "center",
          lineHeight: 18,
        },
      }),
    [theme],
  );

  if (loading && !data)
    return <LoadingSpinner message="Loading portfolio..." />;
  if (error && !data)
    return (
      <ErrorMessage
        message={error}
        onRetry={() => dispatch(fetchPortfolio())}
      />
    );

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
      {/* Hero Section — matches web hero */}
      <View style={styles.heroSection}>
        {user && (
          <Text style={styles.greetingText}>
            Welcome back, {user.name || user.email}
          </Text>
        )}
        <Text style={styles.titleText}>
          Trading <Text style={styles.titleAccent}>Dashboard</Text>
        </Text>
        <Text style={styles.subtitleText}>
          Real-time portfolio monitoring and analytics
        </Text>
      </View>

      {/* Portfolio Overview Cards — matches web grid-cols-4 → 2×2 on mobile */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Portfolio Overview</Text>
        </View>
        <View style={styles.kpiContainer}>
          {kpiData.map((kpi, index) => (
            <KPICard key={index} {...kpi} isLoading={loading} />
          ))}
        </View>
      </View>

      {/* Performance Metrics Table — matches web table section */}
      <View style={styles.sectionAlt}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Performance Metrics</Text>
          <Text style={styles.sectionSubtitle}>
            Historical backtesting results across different strategies
          </Text>
        </View>
        <View style={styles.tableContainer}>
          <View style={styles.tableHeader}>
            <Text style={[styles.tableHeaderCell, styles.col1]}>Strategy</Text>
            <Text style={[styles.tableHeaderCell, styles.col2]}>Sharpe</Text>
            <Text style={[styles.tableHeaderCell, styles.col3]}>Max DD</Text>
            <Text style={[styles.tableHeaderCell, styles.col4]}>Profit F.</Text>
            <Text style={[styles.tableHeaderCell, styles.col5]}>Win %</Text>
          </View>
          {performanceMetrics.map((metric, i) => (
            <View
              key={metric.strategy}
              style={[
                styles.tableRow,
                i === performanceMetrics.length - 1 && styles.tableRowLast,
              ]}
            >
              <Text style={[styles.tableCellStrategy, styles.col1]}>
                {metric.strategy}
              </Text>
              <Text style={[styles.tableCell, styles.col2]}>
                {metric.sharpeRatio}
              </Text>
              <Text style={[styles.tableCell, styles.col3]}>
                {metric.maxDD}
              </Text>
              <Text style={[styles.tableCell, styles.col4]}>
                {metric.profitFactor}
              </Text>
              <Text style={[styles.tableCell, styles.col5]}>
                {metric.winRate}
              </Text>
            </View>
          ))}
        </View>
      </View>

      {/* Hint */}
      <View style={styles.section}>
        <View style={styles.hintCard}>
          <Text style={styles.hintText}>
            Pull down to refresh · Use bottom tabs to explore strategies,
            documentation, and research
          </Text>
        </View>
      </View>
    </ScrollView>
  );
}
