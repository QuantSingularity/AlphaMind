import { useCallback, useEffect, useMemo, useState } from "react";
import { RefreshControl, ScrollView, StyleSheet, View } from "react-native";
import { Text, useTheme } from "react-native-paper";
import { useDispatch, useSelector } from "react-redux";
import KPICard from "../components/KPICard";
import LoadingSpinner from "../components/LoadingSpinner";
import ThemeToggle from "../components/ThemeToggle";
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

  const portfolioState = useSelector((state) => state.portfolio) ?? {};
  const { data = null, loading = false, error = null } = portfolioState;
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
    const zero = "$0.00";
    if (!data) {
      return [
        {
          title: "Portfolio Value",
          value: zero,
          change: "",
          changeColor: theme.colors.onSurfaceVariant,
          icon: "chart-line",
        },
        {
          title: "Daily P&L",
          value: `+${zero}`,
          change: "0.0%",
          changeColor: theme.colors.onSurfaceVariant,
          icon: "trending-up",
        },
        {
          title: "Total P&L",
          value: `+${zero}`,
          change: "0.0%",
          changeColor: theme.colors.onSurfaceVariant,
          icon: "chart-bell-curve-cumulative",
        },
        {
          title: "Cash",
          value: zero,
          change: "",
          changeColor: theme.colors.primary,
          icon: "robot",
        },
      ];
    }

    // The backend portfolio response returns totalValue/cash/dailyPnL/totalPnL.
    // Older shapes used `value`; fall back so both contracts render correctly.
    const totalValue = data.totalValue ?? data.value ?? 0;
    const cash = data.cash ?? 0;
    const dailyPnLNum = data.dailyPnL ?? 0;
    const totalPnLNum = data.totalPnL ?? 0;

    // Daily percent: derive from the prior-day base when not supplied.
    const priorBase = totalValue - dailyPnLNum;
    const dailyPnLPercent =
      data.dailyPnLPercent ?? (priorBase ? (dailyPnLNum / priorBase) * 100 : 0);
    const totalPnLPercent = totalValue
      ? (totalPnLNum / (totalValue - totalPnLNum || 1)) * 100
      : 0;

    const money = (n) =>
      `$${Math.abs(n).toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })}`;
    const signed = (n) => `${n >= 0 ? "+" : "-"}${money(n)}`;
    const pct = (n) => `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
    const dailyColor =
      dailyPnLNum >= 0 ? theme.colors.success : theme.colors.error;
    const totalColor =
      totalPnLNum >= 0 ? theme.colors.success : theme.colors.error;

    return [
      {
        title: "Portfolio Value",
        value: `$${totalValue.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
        change: pct(dailyPnLPercent),
        changeColor: dailyColor,
        icon: "chart-line",
      },
      {
        title: "Daily P&L",
        value: signed(dailyPnLNum),
        change: pct(dailyPnLPercent),
        changeColor: dailyColor,
        icon: "trending-up",
      },
      {
        title: "Total P&L",
        value: signed(totalPnLNum),
        change: pct(totalPnLPercent),
        changeColor: totalColor,
        icon: "chart-bell-curve-cumulative",
      },
      {
        title: "Cash",
        value: `$${cash.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
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
        notice: {
          backgroundColor: theme.colors.surfaceVariant,
          borderRadius: 10,
          marginHorizontal: 16,
          marginTop: 12,
          padding: 12,
        },
        noticeText: {
          color: theme.colors.onSurfaceVariant,
          fontSize: 12,
          lineHeight: 17,
        },
        // Hero section matching web: gradient hero with blue accent
        heroToggle: {
          alignItems: "flex-end",
          marginBottom: 4,
          marginRight: -8,
        },
        heroSection: {
          backgroundColor: theme.colors.surface,
          borderBottomColor: theme.colors.outlineVariant,
          borderBottomWidth: 1,
          paddingBottom: 20,
          paddingHorizontal: 16,
          paddingTop: 24,
        },
        greetingText: {
          color: theme.colors.onSurfaceVariant,
          fontSize: 13,
          marginBottom: 4,
        },
        titleText: {
          color: theme.colors.onBackground,
          fontSize: 28,
          fontWeight: "800",
          letterSpacing: -0.5,
          marginBottom: 4,
        },
        titleAccent: {
          color: theme.colors.primary,
        },
        subtitleText: {
          color: theme.colors.onSurfaceVariant,
          fontSize: 14,
          lineHeight: 20,
        },
        // Section containers
        section: {
          paddingHorizontal: 16,
          paddingVertical: 20,
        },
        sectionAlt: {
          backgroundColor: theme.colors.surfaceVariant,
          paddingHorizontal: 16,
          paddingVertical: 20,
        },
        sectionHeader: {
          marginBottom: 16,
        },
        sectionTitle: {
          color: theme.colors.onBackground,
          fontSize: 20,
          fontWeight: "700",
          marginBottom: 4,
        },
        sectionSubtitle: {
          color: theme.colors.onSurfaceVariant,
          fontSize: 13,
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
          borderColor: theme.colors.outlineVariant,
          borderRadius: 8,
          borderWidth: 1,
          elevation: 2,
          overflow: "hidden",
          shadowColor: "#000",
          shadowOffset: { width: 0, height: 1 },
          shadowOpacity: 0.05,
          shadowRadius: 3,
        },
        tableHeader: {
          backgroundColor: theme.colors.surfaceVariant,
          borderBottomColor: theme.colors.outlineVariant,
          borderBottomWidth: 1,
          flexDirection: "row",
          paddingHorizontal: 12,
          paddingVertical: 10,
        },
        tableHeaderCell: {
          color: theme.colors.onSurfaceVariant,
          fontSize: 10,
          fontWeight: "600",
          letterSpacing: 0.5,
          textTransform: "uppercase",
        },
        tableRow: {
          alignItems: "center",
          borderBottomColor: theme.colors.outlineVariant,
          borderBottomWidth: 1,
          flexDirection: "row",
          paddingHorizontal: 12,
          paddingVertical: 12,
        },
        tableRowLast: {
          borderBottomWidth: 0,
        },
        tableCellStrategy: {
          color: theme.colors.onSurface,
          fontSize: 13,
          fontWeight: "600",
        },
        tableCell: {
          color: theme.colors.onSurfaceVariant,
          fontSize: 13,
        },
        col1: { flex: 2.2 },
        col2: { flex: 1.2 },
        col3: { flex: 1.2 },
        col4: { flex: 1.4 },
        col5: { flex: 1.2 },
        // Info hint card
        hintCard: {
          backgroundColor: theme.colors.surface,
          borderColor: theme.colors.outlineVariant,
          borderRadius: 8,
          borderWidth: 1,
          marginTop: 4,
          padding: 14,
        },
        hintText: {
          color: theme.colors.onSurfaceVariant,
          fontSize: 12,
          lineHeight: 18,
          textAlign: "center",
        },
      }),
    [theme],
  );

  if (loading && !data)
    return <LoadingSpinner message="Loading portfolio..." />;

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
      {error && !data && (
        <View style={styles.notice}>
          <Text style={styles.noticeText}>
            Live data is unavailable right now, so placeholder values are shown.
            Pull down to retry.
          </Text>
        </View>
      )}
      {/* Hero Section - matches web hero */}
      <View style={styles.heroSection}>
        <View style={styles.heroToggle}>
          <ThemeToggle color={theme.colors.onBackground} />
        </View>
        {user && (
          <>
            <Text style={styles.greetingText}>Welcome back, </Text>
            <Text style={styles.greetingText}>{user.name || user.email}</Text>
          </>
        )}
        <Text style={styles.titleText}>
          Trading <Text style={styles.titleAccent}>Dashboard</Text>
        </Text>
        <Text style={styles.subtitleText}>
          Real-time quantitative trading overview
        </Text>
      </View>

      {/* Portfolio Overview Cards - matches web grid-cols-4 → 2×2 on mobile */}
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

      {/* Performance Metrics Table - matches web table section */}
      <View style={styles.sectionAlt}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Performance</Text>
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
