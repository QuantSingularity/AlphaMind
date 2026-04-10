import { render, screen } from "@testing-library/react-native";
import { Provider as PaperProvider } from "react-native-paper";
import FeaturesScreen from "../../screens/FeaturesScreen";

const renderWithPaper = (component) =>
  render(<PaperProvider>{component}</PaperProvider>);

describe("FeaturesScreen", () => {
  it("renders the features title", () => {
    renderWithPaper(<FeaturesScreen />);
    expect(screen.getByText("Features")).toBeTruthy();
  });

  it("renders all feature cards", () => {
    renderWithPaper(<FeaturesScreen />);
    expect(screen.getByText("AI/ML Core")).toBeTruthy();
    expect(screen.getByText("Quantitative Research")).toBeTruthy();
    expect(screen.getByText("Alternative Data Integration")).toBeTruthy();
    expect(screen.getByText("Risk Management")).toBeTruthy();
    expect(screen.getByText("Execution Infrastructure")).toBeTruthy();
    expect(screen.getByText("Portfolio Construction")).toBeTruthy();
  });

  it("renders feature tags", () => {
    renderWithPaper(<FeaturesScreen />);
    expect(screen.getByText("Intelligence")).toBeTruthy();
    expect(screen.getByText("Analytics")).toBeTruthy();
    expect(screen.getByText("Protection")).toBeTruthy();
  });

  it("renders feature descriptions", () => {
    renderWithPaper(<FeaturesScreen />);
    expect(screen.getByText(/advanced machine learning models/i)).toBeTruthy();
  });
});
