import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./index.html",
    "./**/*.{js,ts,jsx,tsx,html}",
  ],
  darkMode: ["class", ".dark"],
  theme: {
    extend: {
      spacing: {
        3: "0.75rem",
      },
    },
    fontFamily: {
      sans: [
        '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto',
        'Helvetica', 'Arial', 'sans-serif'
      ],
    },
  },
  plugins: [],
};

export default config;
