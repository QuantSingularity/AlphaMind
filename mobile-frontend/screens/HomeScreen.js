import { useCallback, useEffect, useMemo } from "react";
import { RefreshControl, ScrollView, StyleSheet, View } from "react-native";
import { Text, useTheme } from "react-native-paper";
import { useDispatch, useSelector } from "react-redux";
import ErrorMessage from "../components/ErrorMessage";
import KPICard from "../components/KPICard";
import LoadingSpinner from "../components/LoadingSpinner";
import { fetchPortfolio } from "../store/slices/portfolioSlice";
import { useState } from "react";

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
          changeColor: theme.colors.outline,
          icon: "chart-line",
        },
        {
          title: "Daily P&L",
          value: "$0.00",
          change: "0.0%",
          changeColor: theme.colors.outline,
          icon: "trending-up",
        },
        {
          title: "Sharpe Ratio",
          value: "0.00",
          change: "",
          changeColor: theme.colors.outline,
          icon: "chart-bell-curve-cumulative",
        },
        {
          title: "Active Strategies",
          value: "0",
          change: "",
          changeColor: theme.colors.outline,
          icon: "robot",
        },
      ];
    }

    const portfolioValue = `$${(data.value ?? 0).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
    const dailyPnLNum = data.dailyPnL ?? 0;
    const dailyPnL = `${dailyPnLNum >= 0 ? "+" : ""}$${Math.abs(
      dailyPnLNum,
    ).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
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
          padding: 16,
        },
        headerSection: {
          marginBottom: 24,
          paddingTop: 8,
        },
        greetingRow: {
          flexDirection: "row",
          alignItems: "center",
          marginBottom: 4,
        },
        welcomeText: {
          fontSize: 13,
          color: theme.colors.onSurfaceVariant,
        },
        userName: {
          fontSize: 13,
          color: theme.colors.primary,
          fontWeight: "700",
        },
        titleText: {
          fontSize: 24,
          fontWeight: "800",
          color: theme.colors.onBackground,
          marginBottom: 4,
        },
        subtitleText: {
          fontSize: 13,
          color: theme.colors.onSurfaceVariant,
        },
        sectionLabel: {
          fontSize: 12,
          fontWeight: "700",
          color: theme.colors.onSurfaceVariant,
          letterSpacing: 1,
          textTransform: "uppercase",
          marginBottom: 12,
        },
        kpiContainer: {
          flexDirection: "row",
          flexWrap: "wrap",
          justifyContent: "space-between",
          marginBottom: 24,
        },
        infoCard: {
          backgroundColor: theme.colors.surfaceVariant,
          borderRadius: 12,
          padding: 16,
          marginTop: 8,
        },
        infoText: {
          color: theme.colors.onSurfaceVariant,
          fontSize: 13,
          textAlign: "center",
          lineHeight: 20,
        },
      }),
    [theme],
  );

  if (loading && !data) {
    return <LoadingSpinner message="Loading portfolio..." />;
  }

  if (error && !data) {
    return (
      <ErrorMessage
        message={error}
        onRetry={() => dispatch(fetchPortfolio())}
      />
    );
  }

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
      <View style={styles.headerSection}>
        {user && (
          <View style={styles.greetingRow}>
            <Text style={styles.welcomeText}>Welcome back, </Text>
            <Text style={styles.userName}>{user.name || user.email}</Text>
          </View>
        )}
        <Text style={styles.titleText}>Dashboard</Text>
        <Text style={styles.subtitleText}>
          Real-time quantitative trading overview
        </Text>
      </View>

      <Text style={styles.sectionLabel}>Performance</Text>
      <View style={styles.kpiContainer}>
        {kpiData.map((kpi, index) => (
          <KPICard key={index} {...kpi} isLoading={loading} />
        ))}
      </View>

      <View style={styles.infoCard}>
        <Text style={styles.infoText}>
          Pull down to refresh · Use bottom tabs to explore features,
          documentation, and research
        </Text>
      </View>
    </ScrollView>
  );
}
