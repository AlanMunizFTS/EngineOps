/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0a0b0f",
          900: "#121319",
          850: "#171922",
          800: "#1d1f2b",
          700: "#282b3a",
          600: "#383c4f",
          500: "#565b74",
          400: "#7b8099",
        },
        ember: {
          50: "#fff4ed",
          100: "#ffe4d1",
          200: "#ffc7a3",
          300: "#ffa06a",
          400: "#ff7a3d",
          500: "#f9591a",
          600: "#ea4510",
          700: "#c2350f",
          800: "#9a2c14",
          900: "#7c2713",
        },
      },
      boxShadow: {
        glow: "0 0 40px -8px rgba(249, 89, 26, 0.35)",
      },
    },
  },
  plugins: [],
};
