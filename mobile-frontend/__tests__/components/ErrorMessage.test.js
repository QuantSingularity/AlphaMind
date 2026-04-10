import { fireEvent, render, screen } from "@testing-library/react-native";
import { Provider as PaperProvider } from "react-native-paper";
import ErrorMessage from "../../components/ErrorMessage";

const renderWithPaper = (component) =>
  render(<PaperProvider>{component}</PaperProvider>);

describe("ErrorMessage", () => {
  it("renders default title", () => {
    renderWithPaper(<ErrorMessage />);
    expect(screen.getByText("Something went wrong")).toBeTruthy();
  });

  it("renders custom title", () => {
    renderWithPaper(<ErrorMessage title="Custom Error" />);
    expect(screen.getByText("Custom Error")).toBeTruthy();
  });

  it("renders message when provided", () => {
    renderWithPaper(<ErrorMessage message="Network failure" />);
    expect(screen.getByText("Network failure")).toBeTruthy();
  });

  it("does not render message when not provided", () => {
    renderWithPaper(<ErrorMessage />);
    expect(screen.queryByText("Network failure")).toBeNull();
  });

  it("renders retry button when onRetry provided", () => {
    const onRetry = jest.fn();
    renderWithPaper(<ErrorMessage onRetry={onRetry} />);
    expect(screen.getByText("Try Again")).toBeTruthy();
  });

  it("does not render retry button when onRetry not provided", () => {
    renderWithPaper(<ErrorMessage />);
    expect(screen.queryByText("Try Again")).toBeNull();
  });

  it("calls onRetry when button pressed", () => {
    const onRetry = jest.fn();
    renderWithPaper(<ErrorMessage onRetry={onRetry} />);
    fireEvent.press(screen.getByText("Try Again"));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("has correct accessibility role", () => {
    renderWithPaper(<ErrorMessage />);
    expect(screen.getByRole("alert")).toBeTruthy();
  });
});
