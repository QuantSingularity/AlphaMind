import { render, screen } from "@testing-library/react-native";
import { Provider as PaperProvider } from "react-native-paper";
import DocumentationScreen from "../../screens/DocumentationScreen";

const renderWithPaper = (component) =>
  render(<PaperProvider>{component}</PaperProvider>);

describe("DocumentationScreen", () => {
  it("renders the documentation title", () => {
    renderWithPaper(<DocumentationScreen />);
    expect(screen.getByText("Documentation")).toBeTruthy();
  });

  it("renders Getting Started section", () => {
    renderWithPaper(<DocumentationScreen />);
    expect(screen.getByText("Getting Started")).toBeTruthy();
    expect(screen.getByText("User Guide")).toBeTruthy();
    expect(screen.getByText("Quick Start Tutorial")).toBeTruthy();
  });

  it("renders API Reference section", () => {
    renderWithPaper(<DocumentationScreen />);
    expect(screen.getByText("API Reference")).toBeTruthy();
    expect(screen.getByText("REST API Docs")).toBeTruthy();
    expect(screen.getByText("Python SDK")).toBeTruthy();
  });

  it("renders Examples & Tutorials section", () => {
    renderWithPaper(<DocumentationScreen />);
    expect(screen.getByText("Examples & Tutorials")).toBeTruthy();
    expect(screen.getByText("Backtesting Example")).toBeTruthy();
    expect(screen.getByText("Model Training Tutorial")).toBeTruthy();
    expect(screen.getByText("Factor Analysis")).toBeTruthy();
  });
});
