import { fetchApi } from './api';

// GET /api/auth/users with optional query params: page, limit, search, role
export async function getUsers({ page = 1, limit = 20, search, role } = {}) {
  const params = new URLSearchParams({ page, limit });
  if (search) params.set('search', search);
  if (role) params.set('role', role);
  return fetchApi(`/auth/users?${params}`);
}

// POST /api/auth/users - create a new user
export async function createUser({ name, email, password, role = 'user' }) {
  return fetchApi('/auth/users', {
    method: 'POST',
    body: JSON.stringify({ name, email, password, role }),
  });
}

// PUT /api/auth/users/{id} - update user
export async function updateUser(userId, { name, email, role, is_active }) {
  return fetchApi(`/auth/users/${userId}`, {
    method: 'PUT',
    body: JSON.stringify({ name, email, role, is_active }),
  });
}

// DELETE /api/auth/users/{id} - deactivate user
export async function deactivateUser(userId) {
  return fetchApi(`/auth/users/${userId}`, { method: 'DELETE' });
}

// POST /api/auth/users/{id}/reset-password
export async function resetPassword(userId, newPassword) {
  return fetchApi(`/auth/users/${userId}/reset-password`, {
    method: 'POST',
    body: JSON.stringify({ new_password: newPassword }),
  });
}
