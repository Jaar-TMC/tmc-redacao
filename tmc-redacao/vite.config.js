import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import svgr from 'vite-plugin-svgr'
import path from 'path'

// Check if building for WordPress
const isWordPress = process.env.BUILD_TARGET === 'wordpress'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    svgr({
      svgrOptions: {
        icon: true,
      },
    }),
  ],

  // Define global constants
  define: {
    'import.meta.env.IS_WORDPRESS': JSON.stringify(isWordPress),
  },

  // Build configuration
  build: isWordPress
    ? {
        // WordPress build: single bundle, no code splitting
        outDir: path.resolve(__dirname, '../tmc-redacao-wp/assets'),
        emptyOutDir: false, // Don't delete existing files (like images)
        rollupOptions: {
          input: path.resolve(__dirname, 'src/main.jsx'),
          output: {
            // Single JS file with fixed name
            entryFileNames: 'js/tmc-redacao.js',
            // CSS file with fixed name
            assetFileNames: (assetInfo) => {
              if (assetInfo.name?.endsWith('.css')) {
                return 'css/tmc-redacao.css'
              }
              // Other assets (images, fonts) go to assets folder
              return 'images/[name][extname]'
            },
            // No code splitting - single bundle (inline all dynamic imports)
            inlineDynamicImports: true,
          },
        },
        // Ensure single CSS file
        cssCodeSplit: false,
        // Source maps for debugging (disable in production)
        sourcemap: process.env.NODE_ENV !== 'production',
        // Minify for production (use esbuild, built into Vite)
        minify: process.env.NODE_ENV === 'production' ? 'esbuild' : false,
      }
    : {
        // Default build: standard Vite output
        outDir: 'dist',
        sourcemap: false,
      },

  // Server configuration for development
  server: {
    port: 5173,
    strictPort: true,
    // CORS for WordPress development
    cors: true,
  },
})
