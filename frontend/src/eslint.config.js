import js from "@eslint/js";
import globals from "globals";
import * as tseslint from "typescript-eslint";
import reactPlugin from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import jsxA11y from "eslint-plugin-jsx-a11y";
import importPlugin from "eslint-plugin-import";

const OFF = "off";
const WARN = "warn";

export default tseslint.config(
  {
    ignores: [
      "dist",
      "coverage",
      "node_modules",
      "cypress",
      ".vite",
      "tailwind-smoke/**",
      "dcw-services/**",
      "dev/**",
      "components/persona/layout/AppShell.tsx",
      "components/deprecated/**",
      "components/persona/__tests__/**",
      "components/ui/__tests__/**",
      "components/settings/SettingsView.tsx",
      "components/chat/Composer.tsx",
      "test/**",
      "src/**"
    ],
  },
  {
    settings: {
      react: {
        version: "detect",
      },
      "import/resolver": {
        node: {
          extensions: [".js", ".jsx", ".ts", ".tsx"],
        },
      },
    },
    plugins: {
      react: reactPlugin,
      "react-hooks": reactHooks,
      "jsx-a11y": jsxA11y,
      import: importPlugin,
    },
    rules: {
      "react/no-unescaped-entities": OFF,
    },
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx}", "**/*.ts", "**/*.tsx"],
    languageOptions: {
      parserOptions: {
        ecmaVersion: "latest",
        sourceType: "module",
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    rules: {
      "react/react-in-jsx-scope": OFF,
      "react/prop-types": OFF,
      "@typescript-eslint/no-unused-vars": [
        WARN,
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "@typescript-eslint/no-explicit-any": WARN,
      "import/order": [
        WARN,
        {
          groups: ["builtin", "external", "internal", "parent", "sibling", "index"],
          "newlines-between": "always",
          alphabetize: { order: "asc", caseInsensitive: true },
          pathGroups: [{ pattern: "@/**", group: "internal" }],
          pathGroupsExcludedImportTypes: ["builtin"],
        },
      ],
      "react-hooks/rules-of-hooks": WARN,
      "react-hooks/exhaustive-deps": WARN,
      "jsx-a11y/alt-text": WARN,
      "@typescript-eslint/ban-ts-comment": WARN,
      "@typescript-eslint/no-empty-object-type": WARN,
      "@typescript-eslint/no-unused-expressions": WARN,
      "prefer-const": WARN,
      "no-unused-vars": OFF,
      "react/jsx-no-undef": WARN,
      "no-empty": WARN,
      "no-empty-pattern": WARN,
    },
  }
);
