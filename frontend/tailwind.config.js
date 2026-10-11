/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0d0f0f",
        panel: "#151818",
        line: "#292e2c",
        lime: "#c8ff3d",
        mist: "#9ba5a0",
        chalk: "#f1f3ed",
      },
      boxShadow: {
        panel: "0 20px 70px rgba(0, 0, 0, 0.28)",
      },
    },
  },
  plugins: [],
};
