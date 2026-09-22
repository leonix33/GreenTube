import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        gt: {
          green: "#1DB954",
          "green-dim": "#169c46",
          charcoal: "#121212",
          panel: "#181818",
          elevated: "#242424",
          muted: "#b3b3b3",
          border: "#2a2a2a",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        player: "0 -8px 32px rgba(0,0,0,0.45)",
      },
    },
  },
  plugins: [],
};

export default config;
