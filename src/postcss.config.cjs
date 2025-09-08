/* --- Tailwind entry directives --- */
@tailwind base;
@tailwind components;
@tailwind utilities;
/* --------------------------------- */


/**
 * PostCSS config for Vite (frontend)
 * – Processes Tailwind CSS directives in src/index.css
 */
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};