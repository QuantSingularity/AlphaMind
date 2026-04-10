import { act, render, screen, waitFor } from "@testing-library/react-native";
import { Provider as PaperProvider } from "react-native-paper";
import ResearchScreen from "../../screens/ResearchScreen";
import { researchService } from "../../services/researchService";

jest.mock("../../services/researchService", () => ({
  researchService: {
    getPapers: jest.fn(),
  },
}));

const renderWithPaper = (component) =>
  render(<PaperProvider>{component}</PaperProvider>);

const mockPapers = [
  {
    id: "1",
    title: "Deep Learning for Market Prediction",
    summary:
      "Exploring LSTM networks in forecasting short-term market movements.",
    authors: ["Dr. John Smith"],
    date: "2025-11-15",
    category: "Machine Learning",
    url: "https://example.com/paper1.pdf",
  },
  {
    id: "2",
    title: "Factor Investing with Alternative Data",
    summary: "A study on integrating satellite imagery data.",
    authors: ["Dr. Alice Johnson"],
    date: "2025-10-20",
    category: "Alternative Data",
    url: "https://example.com/paper2.pdf",
  },
];

describe("ResearchScreen", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("shows loading spinner initially", () => {
    researchService.getPapers.mockReturnValue(new Promise(() => {}));
    renderWithPaper(<ResearchScreen />);
    expect(screen.getByText("Loading research papers...")).toBeTruthy();
  });

  it("renders papers after successful fetch", async () => {
    researchService.getPapers.mockResolvedValueOnce(mockPapers);

    renderWithPaper(<ResearchScreen />);

    await waitFor(() => {
      expect(
        screen.getByText("Deep Learning for Market Prediction"),
      ).toBeTruthy();
      expect(
        screen.getByText("Factor Investing with Alternative Data"),
      ).toBeTruthy();
    });
  });

  it("shows error message when fetch fails", async () => {
    researchService.getPapers.mockRejectedValueOnce({
      message: "Network error",
    });

    renderWithPaper(<ResearchScreen />);

    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeTruthy();
    });
  });

  it("shows empty state when no papers", async () => {
    researchService.getPapers.mockResolvedValueOnce([]);

    renderWithPaper(<ResearchScreen />);

    await waitFor(() => {
      expect(
        screen.getByText("No research papers available at this time."),
      ).toBeTruthy();
    });
  });

  it("shows paper categories as chips", async () => {
    researchService.getPapers.mockResolvedValueOnce(mockPapers);

    renderWithPaper(<ResearchScreen />);

    await waitFor(() => {
      expect(screen.getByText("Machine Learning")).toBeTruthy();
      expect(screen.getByText("Alternative Data")).toBeTruthy();
    });
  });

  it("shows Read Paper buttons for each paper", async () => {
    researchService.getPapers.mockResolvedValueOnce(mockPapers);

    renderWithPaper(<ResearchScreen />);

    await waitFor(() => {
      const readButtons = screen.getAllByText("Read Paper");
      expect(readButtons).toHaveLength(2);
    });
  });
});
