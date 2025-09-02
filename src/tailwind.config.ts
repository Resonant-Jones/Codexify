import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  // Use the standard `.dark` selector for class-based dark mode
  darkMode: ["class", ".dark"],
  theme: { extend: {} },
  plugins: [],
};

export default config;
