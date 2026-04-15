import { useCallback, useEffect, useState } from "react";
import {
  Linking,
  RefreshControl,
  ScrollView,
  StyleSheet,
  View,
} from "react-native";
import { Text, useTheme } from "react-native-paper";
import ErrorMessage from "../components/ErrorMessage";
import LoadingSpinner from "../components/LoadingSpinner";
import { researchService } from "../services/researchService";

const CATEGORY_COLORS = {
  "Machine Learning": "#2563EB",
  "Risk Management": "#D97706",
  "Alternative Data": "#059669",
  "Portfolio Optimization": "#7C3AED",
  "Market Microstructure": "#DC2626",
};

export default function ResearchScreen() {
  const theme = useTheme();
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchPapers = useCallback(async () => {
    try {
      setError(null);
      const data = await researchService.getPapers();
      setPapers(data);
    } catch (err) {
      setError(err.message || "Failed to load research papers");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPapers();
  }, [fetchPapers]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchPapers();
    setRefreshing(false);
  }, [fetchPapers]);

  const handleOpenPaper = useCallback(async (paper) => {
    if (!paper.url) return;
    try {
      const supported = await Linking.canOpenURL(paper.url);
      if (supported) await Linking.openURL(paper.url);
    } catch (_err) {
      /* silent */
    }
  }, []);

  const formatDate = (dateStr) => {
    if (!dateStr) return "";
    try {
      return new Date(dateStr).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  const styles = StyleSheet.create({
    container: {
      flexGrow: 1,
      backgroundColor: theme.colors.background,
    },
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
    headerAccent: { color: theme.colors.primary },
    headerSubtitle: {
      fontSize: 14,
      color: theme.colors.onSurfaceVariant,
      lineHeight: 20,
    },
    listSection: {
      padding: 16,
    },
    sectionLabel: {
      fontSize: 11,
      fontWeight: "700",
      color: theme.colors.onSurfaceVariant,
      letterSpacing: 1,
      textTransform: "uppercase",
      marginBottom: 14,
    },
    // Paper card — matches web bg-white shadow rounded-lg
    card: {
      backgroundColor: theme.colors.surface,
      borderRadius: 8,
      borderWidth: 1,
      borderColor: theme.colors.outlineVariant,
      marginBottom: 12,
      overflow: "hidden",
      shadowColor: "#000",
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.05,
      shadowRadius: 4,
      elevation: 2,
    },
    cardBody: {
      padding: 16,
    },
    cardTop: {
      flexDirection: "row",
      justifyContent: "space-between",
      alignItems: "flex-start",
      marginBottom: 10,
    },
    cardTitle: {
      fontSize: 15,
      fontWeight: "700",
      color: theme.colors.onSurface,
      flex: 1,
      lineHeight: 22,
      marginRight: 8,
    },
    categoryTag: {
      paddingHorizontal: 8,
      paddingVertical: 3,
      borderRadius: 4,
    },
    categoryTagText: {
      fontSize: 10,
      fontWeight: "700",
    },
    summary: {
      fontSize: 13,
      color: theme.colors.onSurfaceVariant,
      lineHeight: 20,
      marginBottom: 12,
    },
    metaRow: {
      flexDirection: "row",
      alignItems: "center",
      gap: 10,
      flexWrap: "wrap",
    },
    authors: {
      fontSize: 12,
      color: theme.colors.onSurfaceVariant,
      fontStyle: "italic",
      flex: 1,
    },
    date: {
      fontSize: 12,
      color: theme.colors.outline,
    },
    // Card footer — matches web table row bottom border style
    cardFooter: {
      borderTopWidth: 1,
      borderTopColor: theme.colors.outlineVariant,
      paddingHorizontal: 16,
      paddingVertical: 10,
      flexDirection: "row",
      alignItems: "center",
    },
    readLink: {
      fontSize: 13,
      fontWeight: "600",
      color: theme.colors.primary,
    },
    arrowIcon: {
      fontSize: 14,
      color: theme.colors.primary,
      marginLeft: 4,
    },
    // Empty state
    emptyContainer: {
      alignItems: "center",
      justifyContent: "center",
      paddingVertical: 60,
      paddingHorizontal: 24,
    },
    emptyIcon: { fontSize: 40, marginBottom: 12 },
    emptyTitle: {
      fontSize: 16,
      fontWeight: "700",
      color: theme.colors.onBackground,
      marginBottom: 6,
      textAlign: "center",
    },
    emptyText: {
      fontSize: 13,
      color: theme.colors.onSurfaceVariant,
      textAlign: "center",
      lineHeight: 20,
    },
  });

  if (loading) return <LoadingSpinner message="Loading research papers..." />;
  if (error) return <ErrorMessage message={error} onRetry={fetchPapers} />;

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
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>
          <Text style={styles.headerAccent}>Research</Text>
        </Text>
        <Text style={styles.headerSubtitle}>
          Latest publications from the AlphaMind research team
        </Text>
      </View>

      <View style={styles.listSection}>
        <Text style={styles.sectionLabel}>Publications</Text>

        {papers.length === 0 ? (
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyIcon}>📄</Text>
            <Text style={styles.emptyTitle}>No papers available</Text>
            <Text style={styles.emptyText}>
              No research papers available at this time. Pull down to refresh.
            </Text>
          </View>
        ) : (
          papers.map((item) => {
            const catColor =
              CATEGORY_COLORS[item.category] || theme.colors.primary;
            return (
              <View key={item.id} style={styles.card}>
                <View style={styles.cardBody}>
                  <View style={styles.cardTop}>
                    <Text style={styles.cardTitle}>{item.title}</Text>
                    {item.category && (
                      <View
                        style={[
                          styles.categoryTag,
                          { backgroundColor: catColor + "18" },
                        ]}
                      >
                        <Text
                          style={[styles.categoryTagText, { color: catColor }]}
                        >
                          {item.category}
                        </Text>
                      </View>
                    )}
                  </View>

                  {item.summary && (
                    <Text style={styles.summary}>{item.summary}</Text>
                  )}

                  <View style={styles.metaRow}>
                    {item.authors && item.authors.length > 0 && (
                      <Text style={styles.authors}>
                        {item.authors.join(", ")}
                      </Text>
                    )}
                    {item.date && (
                      <Text style={styles.date}>{formatDate(item.date)}</Text>
                    )}
                  </View>
                </View>

                {item.url && (
                  <View
                    style={styles.cardFooter}
                    accessible
                    accessibilityRole="button"
                    onStartShouldSetResponder={() => true}
                    onResponderRelease={() => handleOpenPaper(item)}
                  >
                    <Text style={styles.readLink}>Read Paper</Text>
                    <Text style={styles.arrowIcon}>→</Text>
                  </View>
                )}
              </View>
            );
          })
        )}
      </View>
    </ScrollView>
  );
}
