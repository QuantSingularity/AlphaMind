import { render, screen } from "@testing-library/react-native";
import { Provider as PaperProvider } from "react-native-paper";
import KPICard from "../../components/KPICard";

const renderWithPaper = (component) =>
  render(<PaperProvider>{component}</PaperProvider>);

describe("KPICard", () => {
  const defaultProps = {
    title: "Portfolio Value",
    value: "$1,250,345.67",
    change: "+1.27%",
    changeColor: "green",
    icon: "chart-line",
    isLoading: false,
  };

  it("renders title and value correctly", () => {
    renderWithPaper(<KPICard {...defaultProps} />);
    expect(screen.getByText("Portfolio Value")).toBeTruthy();
    expect(screen.getByText("$1,250,345.67")).toBeTruthy();
  });

  it("renders change text when provided", () => {
    renderWithPaper(<KPICard {...defaultProps} />);
    expect(screen.getByText("+1.27%")).toBeTruthy();
  });

  it("does not render change text when change is empty string", () => {
    renderWithPaper(<KPICard {...defaultProps} change="" />);
    expect(screen.queryByText("")).toBeNull();
  });

  it("shows loading dash when isLoading is true", () => {
    renderWithPaper(<KPICard {...defaultProps} isLoading={true} />);
    expect(screen.getByText("-")).toBeTruthy();
    expect(screen.queryByText("$1,250,345.67")).toBeNull();
  });

  it("renders without icon gracefully", () => {
    renderWithPaper(<KPICard {...defaultProps} icon={undefined} />);
    expect(screen.getByText("Portfolio Value")).toBeTruthy();
  });

  it("renders with accessibility label", () => {
    renderWithPaper(<KPICard {...defaultProps} />);
    expect(
      screen.getByLabelText("Portfolio Value: $1,250,345.67"),
    ).toBeTruthy();
  });
});
