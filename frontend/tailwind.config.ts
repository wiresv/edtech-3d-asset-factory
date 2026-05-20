import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#ffffff",
        surface: "#fafafa",
        card: "#ffffff",
        ink: "#0a0a0b",
        "ink-2": "#1f1f23",
        muted: "#71717a",
        "muted-2": "#a1a1aa",
        line: "#e4e4e7",
        "line-2": "#f1f1f3",
        accent: {
          purple: "#5b5bd6",
          red: "#dc2626",
          green: "#16a34a",
          blue: "#2563eb",
          amber: "#d97706",
        },
      },
      borderRadius: {
        card: "16px",
        pill: "999px",
      },
      boxShadow: {
        card: "0 1px 2px rgba(0,0,0,0.04)",
        "card-hover": "0 1px 2px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.06)",
      },
      fontFamily: {
        sans: ["Inter Tight", "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Inter Tight", "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      keyframes: {
        pulseSoft: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.55" },
        },
      },
      animation: {
        pulseSoft: "pulseSoft 1.6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
} satisfies Config;
