import { Linking, ScrollView, StyleSheet, View } from "react-native";
import { List, Text, useTheme } from "react-native-paper";

export default function DocumentationScreen() {
  const theme = useTheme();

  const handlePress = async (url) => {
    if (!url) return;
    try {
      const supported = await Linking.canOpenURL(url);
      if (supported) {
        await Linking.openURL(url);
      }
    } catch (_err) {
      // silently ignore
    }
  };

  const sections = [
    {
      title: "Getting Started",
      items: [
        {
          title: "User Guide",
          description:
            "Step-by-step instructions for setting up and using the platform.",
          icon: "book-open-page-variant-outline",
          url: "https://docs.alphamind.io/guide",
        },
        {
          title: "Quick Start Tutorial",
          description: "A fast-paced introduction to core functionalities.",
          icon: "play-speed",
          url: "https://docs.alphamind.io/quickstart",
        },
      ],
    },
    {
      title: "API Reference",
      items: [
        {
          title: "REST API Docs",
          description: "Detailed reference for all available API endpoints.",
          icon: "api",
          url: "https://docs.alphamind.io/api",
        },
        {
          title: "Python SDK",
          description: "Documentation for the AlphaMind Python client library.",
          icon: "language-python",
          url: "https://docs.alphamind.io/sdk/python",
        },
      ],
    },
    {
      title: "Examples & Tutorials",
      items: [
        {
          title: "Backtesting Example",
          description: "Learn how to backtest trading strategies effectively.",
          icon: "chart-line",
          url: "https://docs.alphamind.io/examples/backtest",
        },
        {
          title: "Model Training Tutorial",
          description: "Guide on training custom AI/ML models.",
          icon: "brain",
          url: "https://docs.alphamind.io/tutorials/model-training",
        },
        {
          title: "Factor Analysis",
          description: "Explore factor-based investing with AlphaMind tools.",
          icon: "magnify-scan",
          url: "https://docs.alphamind.io/examples/factors",
        },
      ],
    },
  ];

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
      lineHeight: 20,
    },
    sectionCard: {
      marginBottom: 16,
      borderRadius: 16,
      backgroundColor: theme.colors.surface,
      overflow: "hidden",
      elevation: 1,
    },
    sectionTitle: {
      fontSize: 12,
      fontWeight: "700",
      letterSpacing: 0.8,
      textTransform: "uppercase",
      color: theme.colors.primary,
      paddingHorizontal: 16,
      paddingTop: 16,
      paddingBottom: 4,
    },
  });

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.headerSection}>
        <Text style={styles.titleText}>Documentation</Text>
        <Text style={styles.subtitleText}>
          Comprehensive resources to help you get the most out of AlphaMind.
        </Text>
      </View>

      {sections.map((section) => (
        <View key={section.title} style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>{section.title}</Text>
          <List.Section>
            {section.items.map((item, idx) => (
              <List.Item
                key={item.title}
                title={item.title}
                description={item.description}
                left={(props) => <List.Icon {...props} icon={item.icon} />}
                right={(props) => <List.Icon {...props} icon="chevron-right" />}
                onPress={() => handlePress(item.url)}
              />
            ))}
          </List.Section>
        </View>
      ))}
    </ScrollView>
  );
}
