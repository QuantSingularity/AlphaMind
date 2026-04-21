import { Linking, ScrollView, StyleSheet, View } from "react-native";
import { Text, useTheme } from "react-native-paper";

const sections = [
  {
    title: "Getting Started",
    items: [
      {
        title: "User Guide",
        description:
          "Step-by-step instructions for setting up and using the platform.",
        icon: "📖",
        url: "https://docs.alphamind.io/guide",
      },
      {
        title: "Quick Start Tutorial",
        description: "A fast-paced introduction to core functionalities.",
        icon: "▶️",
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
        icon: "🔌",
        url: "https://docs.alphamind.io/api",
      },
      {
        title: "Python SDK",
        description: "Documentation for the AlphaMind Python client library.",
        icon: "🐍",
        url: "https://docs.alphamind.io/sdk/python",
      },
      {
        title: "Authentication",
        description: "API key management and OAuth 2.0 integration guide.",
        icon: "🔑",
        url: "https://docs.alphamind.io/auth",
      },
    ],
  },
  {
    title: "Strategy Development",
    items: [
      {
        title: "Backtesting Framework",
        description: "How to run and interpret backtests with historical data.",
        icon: "⏪",
        url: "https://docs.alphamind.io/backtest",
      },
      {
        title: "Custom Strategies",
        description: "Build and deploy your own quantitative strategies.",
        icon: "🧩",
        url: "https://docs.alphamind.io/strategies",
      },
      {
        title: "Risk Parameters",
        description: "Configure risk limits and portfolio constraints.",
        icon: "🛡️",
        url: "https://docs.alphamind.io/risk",
      },
    ],
  },
  {
    title: "Data & Research",
    items: [
      {
        title: "Alternative Data Guide",
        description: "Working with satellite, sentiment, and SEC data feeds.",
        icon: "🛰️",
        url: "https://docs.alphamind.io/altdata",
      },
      {
        title: "Research Papers",
        description: "Academic papers underlying AlphaMind's models.",
        icon: "📄",
        url: "https://docs.alphamind.io/research",
      },
      {
        title: "Model Architecture",
        description: "Deep dive into TFT, RL, and hybrid ML models.",
        icon: "🧠",
        url: "https://docs.alphamind.io/models",
      },
    ],
  },
  {
    title: "Examples & Tutorials",
    items: [
      {
        title: "Backtesting Example",
        description: "Walk through a complete backtest from data to results.",
        icon: "📊",
        url: "https://docs.alphamind.io/examples/backtest",
      },
      {
        title: "Model Training Tutorial",
        description: "Train and evaluate a TFT model on market data.",
        icon: "🤖",
        url: "https://docs.alphamind.io/examples/training",
      },
      {
        title: "Factor Analysis",
        description: "Decompose portfolio returns using factor analysis.",
        icon: "🔬",
        url: "https://docs.alphamind.io/examples/factors",
      },
    ],
  },
];

// Getting Started code block — matches web "Getting Started" section
const gettingStartedCode = `# Clone repository
git clone https://github.com/quantsingularity/AlphaMind.git
cd AlphaMind

# Install dependencies
pip install -r requirements.txt

# Start alternative data ingestion
python -m alternative_data.main \\
  --satellite-api-key $SAT_KEY \\
  --sec-monitor-tickers AAPL,TSLA,NVDA`;

export default function DocumentationScreen() {
  const theme = useTheme();

  const handlePress = async (url) => {
    if (!url) return;
    try {
      const supported = await Linking.canOpenURL(url);
      if (supported) await Linking.openURL(url);
    } catch (_err) {
      /* silent */
    }
  };

  const styles = StyleSheet.create({
    container: {
      flexGrow: 1,
      backgroundColor: theme.colors.background,
    },
    // Header — matches web section header
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
    // Code block — matches web dark code section
    codeSection: {
      margin: 16,
      borderRadius: 8,
      overflow: "hidden",
    },
    codeHeader: {
      backgroundColor: "#1F2937",
      paddingHorizontal: 16,
      paddingVertical: 10,
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
    },
    codeHeaderText: {
      fontSize: 12,
      fontWeight: "600",
      color: "#9CA3AF",
      letterSpacing: 0.5,
    },
    codeDot: {
      flexDirection: "row",
      gap: 6,
    },
    dot: {
      width: 10,
      height: 10,
      borderRadius: 5,
    },
    codeBody: {
      backgroundColor: "#111827",
      padding: 16,
    },
    codeText: {
      fontSize: 12,
      color: "#F3F4F6",
      fontFamily: "monospace",
      lineHeight: 20,
    },
    // Sections
    sectionBlock: {
      paddingHorizontal: 16,
      paddingTop: 20,
      paddingBottom: 4,
    },
    sectionTitle: {
      fontSize: 16,
      fontWeight: "700",
      color: theme.colors.onBackground,
      marginBottom: 12,
      paddingBottom: 8,
      borderBottomWidth: 2,
      borderBottomColor: theme.colors.primary,
    },
    // Doc item — matches web list items
    docItem: {
      backgroundColor: theme.colors.surface,
      borderRadius: 8,
      borderWidth: 1,
      borderColor: theme.colors.outlineVariant,
      padding: 16,
      marginBottom: 10,
      flexDirection: "row",
      alignItems: "flex-start",
      shadowColor: "#000",
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.04,
      shadowRadius: 3,
      elevation: 1,
    },
    docIconBox: {
      width: 38,
      height: 38,
      borderRadius: 8,
      backgroundColor: theme.colors.primaryLight || "#DBEAFE",
      alignItems: "center",
      justifyContent: "center",
      marginRight: 12,
      flexShrink: 0,
    },
    docIcon: { fontSize: 18 },
    docContent: { flex: 1 },
    docTitle: {
      fontSize: 14,
      fontWeight: "700",
      color: theme.colors.onSurface,
      marginBottom: 3,
    },
    docDescription: {
      fontSize: 12,
      color: theme.colors.onSurfaceVariant,
      lineHeight: 18,
    },
    docChevron: {
      fontSize: 16,
      color: theme.colors.primary,
      alignSelf: "center",
      marginLeft: 8,
    },
    bottomPad: { height: 20 },
  });

  return (
    <ScrollView contentContainerStyle={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>
          <Text style={styles.headerAccent}>Documentation</Text>
        </Text>
        <Text style={styles.headerSubtitle}>
          Everything you need to build with AlphaMind
        </Text>
      </View>

      {/* Code block — matches web Getting Started section */}
      <View style={styles.codeSection}>
        <View style={styles.codeHeader}>
          <Text style={styles.codeHeaderText}>QUICK START</Text>
          <View style={styles.codeDot}>
            <View style={[styles.dot, { backgroundColor: "#EF4444" }]} />
            <View style={[styles.dot, { backgroundColor: "#F59E0B" }]} />
            <View style={[styles.dot, { backgroundColor: "#10B981" }]} />
          </View>
        </View>
        <View style={styles.codeBody}>
          <Text style={styles.codeText}>{gettingStartedCode}</Text>
        </View>
      </View>

      {/* Doc sections */}
      {sections.map((section) => (
        <View key={section.title} style={styles.sectionBlock}>
          <Text style={styles.sectionTitle}>{section.title}</Text>
          {section.items.map((item) => (
            <View
              key={item.title}
              style={styles.docItem}
              accessible
              accessibilityRole="button"
              onStartShouldSetResponder={() => true}
              onResponderRelease={() => handlePress(item.url)}
            >
              <View style={styles.docIconBox}>
                <Text style={styles.docIcon}>{item.icon}</Text>
              </View>
              <View style={styles.docContent}>
                <Text style={styles.docTitle}>{item.title}</Text>
                <Text style={styles.docDescription}>{item.description}</Text>
              </View>
              <Text style={styles.docChevron}>›</Text>
            </View>
          ))}
        </View>
      ))}

      <View style={styles.bottomPad} />
    </ScrollView>
  );
}
