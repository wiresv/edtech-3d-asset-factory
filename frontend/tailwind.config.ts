import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#f6f7f9",
        paper: "#ffffff",
        surface: "#f1f2f4",
        card: "#ffffff",
        ink: "#0b0b0d",
        "ink-2": "#33353b",
        muted: "#6b6e76",
        "muted-2": "#9a9da5",
        line: "#e7e8ea",
        "line-2": "#f0f1f3",
        accent: {
          DEFAULT: "#4f5a78",
          red: "#e5484d",
          green: "#30a46c",
          blue: "#3b6ef6",
          amber: "#e0901a",
          violet: "#8b5cf6",
          rose: "#f43f5e",
        },
      },
      borderRadius: {
        card: "14px",
        pill: "999px",
      },
      boxShadow: {
        card: "0 1px 2px 0 rgb(16 17 26 / 0.04)",
        "card-hover":
          "0 2px 4px -1px rgb(16 17 26 / 0.06), 0 8px 24px -6px rgb(16 17 26 / 0.08)",
        pop: "0 18px 44px -14px rgb(10 11 18 / 0.34), 0 4px 12px -4px rgb(10 11 18 / 0.16)",
        ring: "0 0 0 1px rgb(16 17 26 / 0.04)",
      },
      fontFamily: {
        sans: ["Inter Tight", "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Inter Tight", "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      keyframes: {
        fadeIn: {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        riseIn: {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        popIn: {
          from: { opacity: "0", transform: "scale(0.96)" },
          to: { opacity: "1", transform: "scale(1)" },
        },
        revealIn: {
          from: { opacity: "0", transform: "scale(1.03)" },
          to: { opacity: "1", transform: "scale(1)" },
        },
        travel: {
          "0%": { left: "-10%", opacity: "0" },
          "20%, 80%": { opacity: "1" },
          "100%": { left: "110%", opacity: "0" },
        },
        shimmer: {
          from: { transform: "translateX(-100%)" },
          to: { transform: "translateX(100%)" },
        },
        breathe: {
          "0%, 100%": { opacity: "0.35", transform: "scale(1)" },
          "50%": { opacity: "0.85", transform: "scale(1.05)" },
        },
        spinSlow: {
          from: { transform: "rotate(0deg)" },
          to: { transform: "rotate(360deg)" },
        },
        drawIn: {
          from: { strokeDashoffset: "1" },
          to: { strokeDashoffset: "0" },
        },
      },
      animation: {
        fadeIn: "fadeIn 0.35s ease both",
        riseIn: "riseIn 0.5s cubic-bezier(0.22,1,0.36,1) both",
        popIn: "popIn 0.22s cubic-bezier(0.22,1,0.36,1) both",
        revealIn: "revealIn 0.5s cubic-bezier(0.22,1,0.36,1) both",
        travel: "travel 1.5s ease-in-out infinite",
        shimmer: "shimmer 1.7s ease-in-out infinite",
        breathe: "breathe 2.4s ease-in-out infinite",
        spinSlow: "spinSlow 9s linear infinite",
        drawIn: "drawIn 0.45s ease-out forwards",
      },
    },
  },
  plugins: [],
} satisfies Config;
