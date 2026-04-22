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
import LoginScreen from "../../screens/LoginScreen";
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
    reducer: {
      auth: authReducer,
    },
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

describe("LoginScreen", () => {
  beforeEach(() => {
    mockNavigate.mockClear();
  });

  it("renders login form correctly", () => {
    renderWithProviders(
      <LoginScreen navigation={{ navigate: mockNavigate }} />,
    );

    expect(screen.getByText("AlphaMind")).toBeTruthy();
    expect(screen.getByText("Sign in to your trading dashboard")).toBeTruthy();
    expect(screen.getByText("Sign In")).toBeTruthy();
  });

  it("allows input in email and password fields", () => {
    renderWithProviders(
      <LoginScreen navigation={{ navigate: mockNavigate }} />,
    );

    const emailInput = screen.getByTestId("email-input");
    const passwordInput = screen.getByTestId("password-input");

    fireEvent.changeText(emailInput, "test@example.com");
    fireEvent.changeText(passwordInput, "password123");

    expect(emailInput.props.value).toBe("test@example.com");
    expect(passwordInput.props.value).toBe("password123");
  });

  it("navigates to register screen when link is pressed", () => {
    renderWithProviders(
      <LoginScreen navigation={{ navigate: mockNavigate }} />,
    );

    const registerButton = screen.getByText("Create an Account");
    fireEvent.press(registerButton);

    expect(mockNavigate).toHaveBeenCalledWith("Register");
  });

  it("shows error for invalid email format", async () => {
    renderWithProviders(
      <LoginScreen navigation={{ navigate: mockNavigate }} />,
    );

    const emailInput = screen.getByTestId("email-input");
    const passwordInput = screen.getByTestId("password-input");
    fireEvent.changeText(emailInput, "notanemail");
    fireEvent.changeText(passwordInput, "password123");

    const signInButton = screen.getByText("Sign In");
    fireEvent.press(signInButton);

    await waitFor(() => {
      expect(
        screen.getByText("Please enter a valid email address"),
      ).toBeTruthy();
    });
  });

  it("shows error for missing email", async () => {
    renderWithProviders(
      <LoginScreen navigation={{ navigate: mockNavigate }} />,
    );

    fireEvent.changeText(screen.getByTestId("password-input"), "password123");
    fireEvent.press(screen.getByText("Sign In"));

    await waitFor(() => {
      expect(screen.getByText("Email is required")).toBeTruthy();
    });
  });

  it("shows error for missing password", async () => {
    renderWithProviders(
      <LoginScreen navigation={{ navigate: mockNavigate }} />,
    );

    fireEvent.changeText(screen.getByTestId("email-input"), "test@example.com");
    fireEvent.press(screen.getByText("Sign In"));

    await waitFor(() => {
      expect(screen.getByText("Password is required")).toBeTruthy();
    });
  });
});
