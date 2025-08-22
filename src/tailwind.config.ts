import type { Config } from "tailwindcss"

export default {
  darkMode: ["class", "dark"],
  content: ["./index.html", "./**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--color-bg)",
        surface: "var(--color-surface)",
        fg: "var(--color-fg)",
        muted: "var(--color-muted)",
        primary: "var(--color-primary)"
      },
      borderRadius: {
        DEFAULT: "var(--radius)"
      }
    }
  }
} satisfies Config
