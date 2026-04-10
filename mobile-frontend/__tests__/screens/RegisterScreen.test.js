import { NavigationContainer } from "@react-navigation/native";
import { configureStore } from "@reduxjs/toolkit";
import {
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react-native";
import { Provider as PaperProvider } from "react-native-paper";
import { Provider } from "react-redux";
import RegisterScreen from "../../screens/RegisterScreen";
import authReducer from "../../store/slices/authSlice";

const mockNavigate = jest.fn();

jest.mock("@react-navigation/native", () => {
  const actualNav = jest.requireActual("@react-navigation/native");
  return {
    ...actualNav,
    useNavigation: () => ({
      navigate: mockNavigate,
    }),
  };
});

const createMockStore = () =>
  configureStore({
    reducer: { auth: authReducer },
  });

const renderWithProviders = (component) => {
  const store = createMockStore();
  return render(
    <Provider store={store}>
      <PaperProvider>
        <NavigationContainer>{component}</NavigationContainer>
      </PaperProvider>
    </Provider>,
  );
};

describe("RegisterScreen", () => {
  beforeEach(() => {
    mockNavigate.mockClear();
  });

  it("renders register form correctly", () => {
    renderWithProviders(
      <RegisterScreen navigation={{ navigate: mockNavigate }} />,
    );
    expect(screen.getByText("Create Account")).toBeTruthy();
    expect(screen.getByText("Join AlphaMind to start trading")).toBeTruthy();
  });

  it("allows input in all fields", () => {
    renderWithProviders(
      <RegisterScreen navigation={{ navigate: mockNavigate }} />,
    );

    const nameInput = screen.getByTestId("name-input");
    const emailInput = screen.getByTestId("email-input");
    const passwordInput = screen.getByTestId("password-input");
    const confirmInput = screen.getByTestId("confirm-password-input");

    fireEvent.changeText(nameInput, "John Doe");
    fireEvent.changeText(emailInput, "john@example.com");
    fireEvent.changeText(passwordInput, "password123");
    fireEvent.changeText(confirmInput, "password123");

    expect(nameInput.props.value).toBe("John Doe");
    expect(emailInput.props.value).toBe("john@example.com");
    expect(passwordInput.props.value).toBe("password123");
    expect(confirmInput.props.value).toBe("password123");
  });

  it("shows error for missing name", async () => {
    renderWithProviders(
      <RegisterScreen navigation={{ navigate: mockNavigate }} />,
    );

    const emailInput = screen.getByTestId("email-input");
    const passwordInput = screen.getByTestId("password-input");
    const confirmInput = screen.getByTestId("confirm-password-input");

    fireEvent.changeText(emailInput, "john@example.com");
    fireEvent.changeText(passwordInput, "password123");
    fireEvent.changeText(confirmInput, "password123");

    const submitButton = screen.getByText("Create Account");
    fireEvent.press(submitButton);

    await waitFor(() => {
      expect(screen.getByText("Full name is required")).toBeTruthy();
    });
  });

  it("shows error for invalid email", async () => {
    renderWithProviders(
      <RegisterScreen navigation={{ navigate: mockNavigate }} />,
    );

    fireEvent.changeText(screen.getByTestId("name-input"), "John Doe");
    fireEvent.changeText(screen.getByTestId("email-input"), "notanemail");
    fireEvent.changeText(screen.getByTestId("password-input"), "password123");
    fireEvent.changeText(
      screen.getByTestId("confirm-password-input"),
      "password123",
    );

    fireEvent.press(screen.getByText("Create Account"));

    await waitFor(() => {
      expect(
        screen.getByText("Please enter a valid email address"),
      ).toBeTruthy();
    });
  });

  it("shows error when passwords do not match", async () => {
    renderWithProviders(
      <RegisterScreen navigation={{ navigate: mockNavigate }} />,
    );

    fireEvent.changeText(screen.getByTestId("name-input"), "John Doe");
    fireEvent.changeText(screen.getByTestId("email-input"), "john@example.com");
    fireEvent.changeText(screen.getByTestId("password-input"), "password123");
    fireEvent.changeText(
      screen.getByTestId("confirm-password-input"),
      "different",
    );

    fireEvent.press(screen.getByText("Create Account"));

    await waitFor(() => {
      expect(screen.getByText("Passwords do not match")).toBeTruthy();
    });
  });

  it("shows error for short password", async () => {
    renderWithProviders(
      <RegisterScreen navigation={{ navigate: mockNavigate }} />,
    );

    fireEvent.changeText(screen.getByTestId("name-input"), "John Doe");
    fireEvent.changeText(screen.getByTestId("email-input"), "john@example.com");
    fireEvent.changeText(screen.getByTestId("password-input"), "short");
    fireEvent.changeText(screen.getByTestId("confirm-password-input"), "short");

    fireEvent.press(screen.getByText("Create Account"));

    await waitFor(() => {
      expect(
        screen.getByText("Password must be at least 8 characters"),
      ).toBeTruthy();
    });
  });

  it("navigates to login when link is pressed", () => {
    renderWithProviders(
      <RegisterScreen navigation={{ navigate: mockNavigate }} />,
    );

    fireEvent.press(screen.getByText("Already have an account? Sign In"));
    expect(mockNavigate).toHaveBeenCalledWith("Login");
  });
});
