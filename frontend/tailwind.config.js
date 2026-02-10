/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ledger: {
          paper: "var(--ledger-paper)",
          ink: "var(--ledger-ink)",
          smoke: "var(--ledger-smoke)",
          accent: "var(--ledger-accent)",
          accentSoft: "var(--ledger-accent-soft)",
          line: "var(--ledger-line)",
        },
      },
      boxShadow: {
        ledger: "0 20px 45px rgba(20, 20, 20, 0.11)",
      },
      keyframes: {
        "lift-in": {
          "0%": { opacity: "0", transform: "translateY(22px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseDot: {
          "0%, 100%": { transform: "scale(1)", opacity: "0.7" },
          "50%": { transform: "scale(1.18)", opacity: "1" },
        },
      },
      animation: {
        "lift-in": "lift-in 480ms ease-out forwards",
        pulseDot: "pulseDot 1.2s ease-in-out infinite",
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "serif"],
        body: ["Manrope", "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};
