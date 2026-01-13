/**
 * Feature Flags for TMC Redação
 *
 * Controls which features are visible/enabled in the application.
 * Used to incrementally develop the MVP while preserving the full mockup design.
 *
 * Version Control Strategy:
 * - v0.0.0-mockup: All features visible (mock data)
 * - v0.1.0-mvp: Core features only (real data)
 * - v1.0.0: Full release
 */

export const FEATURES = {
  // ==========================================
  // MVP Features (ENABLED) - Core functionality
  // ==========================================

  /** RSS Feed as source for article generation */
  RSS_FEED: true,

  /** Manual text paste as source (Link da Web) */
  PASTED_TEXT: true,

  /** AI-powered article generation */
  AI_GENERATION: true,

  /** SEO Analyzer panel with real-time scoring */
  SEO_ANALYZER: true,

  /** Simple textarea editor */
  SIMPLE_EDITOR: true,

  /** Copy article to clipboard */
  COPY_TO_CLIPBOARD: true,

  /** Tag display on article cards */
  TAG_DISPLAY: true,

  // ==========================================
  // Post-MVP Features (DISABLED) - Coming later
  // ==========================================

  /** Video transcription via Speech-to-Text */
  VIDEO_TRANSCRIPTION: false,

  /** Google Trends integration */
  GOOGLE_TRENDS: false,

  /** Twitter/X trends sidebar */
  TWITTER_TRENDS: false,

  /** User authentication system */
  USER_AUTH: false,

  /** Rich text editor (TipTap/Slate) */
  RICH_TEXT_EDITOR: false,

  /** PDF export functionality */
  EXPORT_PDF: false,

  /** Markdown/HTML export */
  EXPORT_FORMATS: false,

  /** AI-powered formatting buttons */
  AI_FORMATTING: false,

  /** Database persistence for articles */
  DATABASE_PERSISTENCE: false,

  /** LocalStorage draft persistence */
  LOCALSTORAGE_DRAFTS: false,

  /** Tag selection (select which tags to keep) */
  TAG_SELECTION: false,

  /** Minhas Matérias edit functionality */
  EDIT_SAVED_ARTICLES: false,

  /** Tema em Alta recognition display */
  TRENDING_THEMES: false,
};

/**
 * Helper function to check if a feature is enabled
 * @param {keyof FEATURES} featureName - The feature to check
 * @returns {boolean} Whether the feature is enabled
 */
export const isFeatureEnabled = (featureName) => {
  return FEATURES[featureName] === true;
};

/**
 * Helper function to conditionally render based on feature flag
 * Usage: {renderIf(FEATURES.VIDEO_TRANSCRIPTION, <VideoOption />)}
 * @param {boolean} condition - The feature flag value
 * @param {React.ReactNode} component - Component to render if enabled
 * @returns {React.ReactNode | null}
 */
export const renderIf = (condition, component) => {
  return condition ? component : null;
};

export default FEATURES;
