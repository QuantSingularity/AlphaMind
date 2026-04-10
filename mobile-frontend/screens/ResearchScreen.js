import { useCallback, useEffect, useState } from "react";
import {
  Linking,
  RefreshControl,
  ScrollView,
  StyleSheet,
  View,
} from "react-native";
import { Button, Card, Chip, Text, useTheme } from "react-native-paper";
import ErrorMessage from "../components/ErrorMessage";
import LoadingSpinner from "../components/LoadingSpinner";
import { researchService } from "../services/researchService";

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
      if (supported) {
        await Linking.openURL(paper.url);
      }
    } catch (_err) {
      // silently ignore if URL cannot be opened
    }
  }, []);

  const formatDate = (dateStr) => {
    if (!dateStr) return "";
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString("en-US", {
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
      padding: 20,
      backgroundColor: theme.colors.background,
    },
    headerSection: {
      marginBottom: 24,
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
    },
    card: {
      marginBottom: 16,
      borderRadius: 16,
      backgroundColor: theme.colors.surface,
      elevation: 2,
    },
    cardContent: {
      padding: 16,
      paddingBottom: 8,
    },
    cardTitle: {
      fontSize: 15,
      fontWeight: "700",
      color: theme.colors.onSurface,
      marginBottom: 8,
      lineHeight: 22,
    },
    summary: {
      fontSize: 13,
      color: theme.colors.onSurfaceVariant,
      lineHeight: 20,
      marginBottom: 12,
    },
    metaRow: {
      flexDirection: "row",
      flexWrap: "wrap",
      gap: 8,
      alignItems: "center",
      marginBottom: 8,
    },
    categoryChip: {
      height: 26,
    },
    categoryChipText: {
      fontSize: 10,
      fontWeight: "700",
    },
    authors: {
      fontSize: 12,
      color: theme.colors.onSurfaceVariant,
      fontStyle: "italic",
    },
    date: {
      fontSize: 12,
      color: theme.colors.outline,
    },
    cardActions: {
      paddingHorizontal: 8,
      paddingBottom: 8,
    },
    emptyContainer: {
      alignItems: "center",
      marginTop: 60,
      padding: 20,
    },
    emptyIcon: {
      fontSize: 40,
      marginBottom: 12,
    },
    emptyText: {
      fontSize: 15,
      color: theme.colors.onSurfaceVariant,
      textAlign: "center",
    },
  });

  if (loading) {
    return <LoadingSpinner message="Loading research papers..." />;
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={fetchPapers} />;
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
        <Text style={styles.titleText}>Research</Text>
        <Text style={styles.subtitleText}>
          Latest publications from the AlphaMind research team
        </Text>
      </View>

      {papers.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyIcon}>📄</Text>
          <Text style={styles.emptyText}>
            No research papers available at this time.
          </Text>
        </View>
      ) : (
        papers.map((item) => (
          <Card key={item.id} style={styles.card}>
            <View style={styles.cardContent}>
              <Text style={styles.cardTitle}>{item.title}</Text>
              <Text style={styles.summary}>{item.summary}</Text>
              <View style={styles.metaRow}>
                {item.category && (
                  <Chip
                    style={[
                      styles.categoryChip,
                      { backgroundColor: theme.colors.primary + "22" },
                    ]}
                    textStyle={[
                      styles.categoryChipText,
                      { color: theme.colors.primary },
                    ]}
                    compact
                  >
                    {item.category}
                  </Chip>
                )}
                {item.date && (
                  <Text style={styles.date}>{formatDate(item.date)}</Text>
                )}
              </View>
              {item.authors && item.authors.length > 0 && (
                <Text style={styles.authors}>{item.authors.join(", ")}</Text>
              )}
            </View>
            <View style={styles.cardActions}>
              <Button mode="text" onPress={() => handleOpenPaper(item)} compact>
                Read Paper
              </Button>
            </View>
          </Card>
        ))
      )}
    </ScrollView>
  );
}
