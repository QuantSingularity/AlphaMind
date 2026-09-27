import { useCallback, useEffect, useMemo, useState } from "react";
import { RefreshControl, ScrollView, StyleSheet, View } from "react-native";
import { Icon, Text, useTheme } from "react-native-paper";
import { useDispatch, useSelector } from "react-redux";
import KPICard from "../components/KPICard";
import { fetchHoldings, fetchPortfolio } from "../store/slices/portfolioSlice";

const formatCurrency = (n) =>
  `$${Number(n ?? 0).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;

export default function PortfolioScreen() {
  const theme = useTheme();
  const dispatch = useDispatch();
  const portfolioState = useSelector((state) => state.portfolio) ?? {};
  const { data = null, holdings = [], loading = false } = portfolioState;
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    dispatch(fetchPortfolio());
    dispatch(fetchHoldings());
  }, [dispatch]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await Promise.all([dispatch(fetchPortfolio()), dispatch(fetchHoldings())]);
    setRefreshing(false);
  }, [dispatch]);

  const kpis = useMemo(() => {
    const value = data?.totalValue ?? data?.value ?? 0;
    const pnl = data?.dailyPnL ?? 0;
    const priorBase = value - pnl;
    const pnlPct =
      data?.dailyPnLPercent ?? (priorBase ? (pnl / priorBase) * 100 : 0);
    const changeColor = pnlPct >= 0 ? theme.colors.success : theme.colors.error;
    return [
      {
        title: "Portfolio Value",
        value: formatCurrency(value),
        change: `${pnlPct >= 0 ? "+" : ""}${pnlPct.toFixed(2)}%`,
        changeColor,
        icon: "chart-line",
      },
      {
        title: "Daily P&L",
        value: `${pnl >= 0 ? "+" : ""}${formatCurrency(Math.abs(pnl)).replace("$", "$")}`,
        change: `${pnlPct >= 0 ? "+" : ""}${pnlPct.toFixed(2)}%`,
        changeColor,
        icon: "trending-up",
      },
      {
        title: "Cash",
        value: formatCurrency(data?.cash ?? 0),
        change: "",
        changeColor: theme.colors.primary,
        icon: "chart-bell-curve-cumulative",
      },
      {
        title: "Positions",
        value: String(holdings?.length ?? 0),
        change: "",
        changeColor: theme.colors.primary,
        icon: "robot",
      },
    ];
  }, [data, holdings, theme.colors]);

  const styles = useMemo(() => createStyles(theme), [theme]);

  const normalizedHoldings = (holdings ?? []).map((h, i) => ({
    key: h.id ?? h.ticker ?? h.symbol ?? String(i),
    ticker: h.ticker ?? h.symbol ?? "-",
    name: h.name ?? h.sector ?? "",
    value: h.value ?? h.marketValue ?? 0,
    weight: h.weight ?? h.percentage ?? null,
    pnl: h.unrealizedPnL ?? h.pnl ?? null,
  }));

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
        <Text style={styles.title}>Portfolio</Text>
        <Text style={styles.subtitle}>
          Holdings, allocation, and current exposure
        </Text>
      </View>

      <View style={styles.section}>
        <View style={styles.kpiGrid}>
          {kpis.map((kpi, i) => (
            <KPICard key={i} {...kpi} isLoading={loading && !data} />
          ))}
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Holdings</Text>
        {normalizedHoldings.length === 0 ? (
          <View style={styles.emptyCard}>
            <Icon
              source="briefcase-outline"
              size={28}
              color={theme.colors.onSurfaceFaint}
            />
            <Text style={styles.emptyTitle}>No holdings to display</Text>
            <Text style={styles.emptyHint}>
              Connect a live data source or activate a strategy to populate
              positions. Pull down to refresh.
            </Text>
          </View>
        ) : (
          <View style={styles.table}>
            <View style={styles.tableHeader}>
              <Text style={[styles.th, styles.cTicker]}>Ticker</Text>
              <Text style={[styles.th, styles.cValue]}>Value</Text>
              <Text style={[styles.th, styles.cWeight]}>Weight</Text>
              <Text style={[styles.th, styles.cPnl]}>P&L</Text>
            </View>
            {normalizedHoldings.map((h, i) => {
              const pnlColor =
                h.pnl == null
                  ? theme.colors.onSurfaceVariant
                  : h.pnl >= 0
                    ? theme.colors.success
                    : theme.colors.error;
              return (
                <View
                  key={h.key}
                  style={[
                    styles.tableRow,
                    i === normalizedHoldings.length - 1 && styles.tableRowLast,
                  ]}
                >
                  <View style={styles.cTicker}>
                    <Text style={styles.tickerText}>{h.ticker}</Text>
                    {!!h.name && <Text style={styles.nameText}>{h.name}</Text>}
                  </View>
                  <Text style={[styles.td, styles.cValue]}>
                    {formatCurrency(h.value)}
                  </Text>
                  <Text style={[styles.td, styles.cWeight]}>
                    {h.weight == null
                      ? "-"
                      : `${(h.weight <= 1 ? h.weight * 100 : h.weight).toFixed(1)}%`}
                  </Text>
                  <Text style={[styles.td, styles.cPnl, { color: pnlColor }]}>
                    {h.pnl == null ? "-" : formatCurrency(h.pnl)}
                  </Text>
                </View>
              );
            })}
          </View>
        )}
      </View>
    </ScrollView>
  );
}

const createStyles = (theme) =>
  StyleSheet.create({
    cPnl: { flex: 1.4, textAlign: "right" },
    cTicker: { flex: 2 },
    cValue: { flex: 1.6, textAlign: "right" },
    cWeight: { flex: 1.1, textAlign: "right" },
    container: {
      backgroundColor: theme.colors.background,
      flexGrow: 1,
    },
    emptyCard: {
      alignItems: "center",
      backgroundColor: theme.colors.surface,
      borderColor: theme.colors.outlineVariant,
      borderRadius: 12,
      borderWidth: 1,
      padding: 28,
    },
    emptyHint: {
      color: theme.colors.onSurfaceVariant,
      fontSize: 13,
      lineHeight: 19,
      textAlign: "center",
    },
    emptyTitle: {
      color: theme.colors.onSurface,
      fontSize: 15,
      fontWeight: "700",
      marginBottom: 4,
      marginTop: 10,
    },
    hero: {
      backgroundColor: theme.colors.surface,
      borderBottomColor: theme.colors.outlineVariant,
      borderBottomWidth: 1,
      paddingBottom: 18,
      paddingHorizontal: 16,
      paddingTop: 24,
    },
    kpiGrid: {
      flexDirection: "row",
      flexWrap: "wrap",
      justifyContent: "space-between",
    },
    nameText: {
      color: theme.colors.onSurfaceFaint,
      fontSize: 11,
    },
    section: {
      paddingHorizontal: 16,
      paddingVertical: 18,
    },
    sectionTitle: {
      color: theme.colors.onBackground,
      fontSize: 18,
      fontWeight: "700",
      marginBottom: 12,
    },
    subtitle: {
      color: theme.colors.onSurfaceVariant,
      fontSize: 14,
    },
    table: {
      backgroundColor: theme.colors.surface,
      borderColor: theme.colors.outlineVariant,
      borderRadius: 12,
      borderWidth: 1,
      overflow: "hidden",
    },
    tableHeader: {
      backgroundColor: theme.colors.surfaceVariant,
      borderBottomColor: theme.colors.outlineVariant,
      borderBottomWidth: 1,
      flexDirection: "row",
      paddingHorizontal: 12,
      paddingVertical: 10,
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
    td: {
      color: theme.colors.onSurfaceVariant,
      fontSize: 13,
      fontVariant: ["tabular-nums"],
    },
    th: {
      color: theme.colors.onSurfaceVariant,
      fontSize: 10,
      fontWeight: "700",
      letterSpacing: 0.5,
      textTransform: "uppercase",
    },
    tickerText: {
      color: theme.colors.onSurface,
      fontSize: 13,
      fontWeight: "700",
    },
    title: {
      color: theme.colors.onBackground,
      fontSize: 28,
      fontWeight: "800",
      letterSpacing: -0.5,
      marginBottom: 4,
    },
  });
