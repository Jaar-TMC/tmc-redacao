/**
 * Auth Service for TMC Redação
 *
 * Handles authentication API calls and token management.
 * Access token stored in memory only (not localStorage) for security.
 * Refresh token handled as httpOnly cookie by the browser.
 */

import { fetchApi } from './api.js';

// Module-level token storage (memory only, not localStorage)
let _accessToken = null;

export function setAuthToken(token) {
  _accessToken = token;
}

export function getAuthToken() {
  return _accessToken;
}

export function clearAuthToken() {
  _accessToken = null;
}

/**
 * Login with email and password
 * @param {string} email
 * @param {string} password
 * @param {boolean} [rememberMe=false] - Extend refresh token duration
 * @returns {Promise<{access_token: string, user: Object}>}
 */
export async function authLogin(email, password, rememberMe = false) {
  return fetchApi('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password, remember_me: rememberMe }),
    credentials: 'include',
  });
}

/**
 * Refresh access token using httpOnly cookie
 * @returns {Promise<{access_token: string}>}
 */
export async function authRefresh() {
  return fetchApi('/auth/refresh', {
    method: 'POST',
    credentials: 'include',
  });
}

/**
 * Logout - clears tokens on server and client
 * @returns {Promise<void>}
 */
export async function authLogout() {
  return fetchApi('/auth/logout', {
    method: 'POST',
    credentials: 'include',
  });
}

/**
 * Get current authenticated user
 * @returns {Promise<Object>} User object
 */
export async function authGetMe() {
  return fetchApi('/auth/me');
}

/**
 * Update current user profile
 * @param {Object} data - Fields to update (e.g. { is_new_user: false })
 * @returns {Promise<Object>} Updated user object
 */
export async function authUpdateMe(data) {
  return fetchApi('/auth/me', {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}
