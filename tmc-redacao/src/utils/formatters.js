/**
 * Formatting utilities for dates and numbers
 */

/**
 * Format a date as relative time in Portuguese (e.g., "ha 5 min", "ha 2h")
 * @param {Date|string} date - Date to format
 * @returns {string} Relative time string
 */
export const formatRelativeTime = (date) => {
  if (!date) return "nunca";

  const now = new Date();
  const dateObj = date instanceof Date ? date : new Date(date);

  if (isNaN(dateObj.getTime())) return "nunca";

  const diffInSeconds = Math.floor((now - dateObj) / 1000);

  if (diffInSeconds < 60) return "agora mesmo";
  if (diffInSeconds < 3600) return `há ${Math.floor(diffInSeconds / 60)} min`;
  if (diffInSeconds < 86400) return `há ${Math.floor(diffInSeconds / 3600)}h`;
  if (diffInSeconds < 604800) return `há ${Math.floor(diffInSeconds / 86400)} dias`;
  return dateObj.toLocaleDateString("pt-BR");
};

/**
 * Format a number in Brazilian locale (e.g., 1.234,56)
 * @param {number} num - Number to format
 * @returns {string} Formatted number string
 */
export const formatNumber = (num) => {
  return new Intl.NumberFormat('pt-BR').format(num);
};
