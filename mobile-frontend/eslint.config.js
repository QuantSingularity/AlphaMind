import babelParser from "@babel/eslint-parser";
import js from "@eslint/js";
import reactPlugin from "eslint-plugin-react";
import reactNativePlugin from "eslint-plugin-react-native";

export default [
  {
    ignores: ["node_modules/**"],
  },
  js.configs.recommended,
  {
    files: ["**/*.{js,jsx}"], // Apply rules to JS and JSX files
    languageOptions: {
      parser: babelParser,
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
        requireConfigFile: false, // Important for @babel/eslint-parser
        babelOptions: {
          presets: ["@babel/preset-react"], // Or your specific Babel config
        },
      },
      globals: {
        // JS / React Native / Node runtime globals
        console: "readonly",
        process: "readonly",
        require: "readonly",
        module: "writable",
        __dirname: "readonly",
        __filename: "readonly",
        global: "writable",
        fetch: "readonly",
        setTimeout: "readonly",
        clearTimeout: "readonly",
        setInterval: "readonly",
        clearInterval: "readonly",
        __DEV__: true,
        // Jest test globals
        jest: true,
        expect: true,
        test: true,
        it: true,
        describe: true,
        beforeAll: true,
        afterAll: true,
        beforeEach: true,
        afterEach: true,
      },
    },
    plugins: {
      react: reactPlugin,
      "react-native": reactNativePlugin,
    },
    rules: {
      // Start with recommended rules for React and React Native
      ...reactPlugin.configs.recommended.rules,
      ...reactNativePlugin.configs.all.rules,
      // Add specific rule overrides if necessary
      "react/react-in-jsx-scope": "off", // Often not needed with modern React
      // This is a plain-JS (no TypeScript / PropTypes) codebase, so prop-type
      // validation is intentionally disabled rather than annotating every prop.
      "react/prop-types": "off",
      // Treat underscore-prefixed args/vars/caught errors as intentionally unused.
      "no-unused-vars": [
        "error",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
        },
      ],
      "react-native/no-unused-styles": "warn",
      "react-native/split-platform-components": "warn",
      "react-native/no-inline-styles": "warn",
      "react-native/no-color-literals": "warn",
      "react-native/no-raw-text": "warn", // Can be strict, adjust as needed
      // Purely cosmetic style ordering - keep as guidance, not a build failure
      // (consistent with the other cosmetic rules above being warnings).
      "react-native/sort-styles": "warn",
    },
    settings: {
      react: {
        version: "detect", // Automatically detect React version
      },
    },
  },
];
