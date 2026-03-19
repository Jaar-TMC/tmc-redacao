import { fetchApi } from './api';

export async function getCostOverview(period, { signal } = {}) {
  return fetchApi(`/costs/overview?period=${period}`, { signal });
}

export async function getCostTrends({ granularity, start, end, period } = {}, { signal } = {}) {
  const params = new URLSearchParams();
  if (granularity) params.set('granularity', granularity);
  if (start) params.set('start_date', start);
  if (end) params.set('end_date', end);
  if (period) params.set('period', period);
  return fetchApi(`/costs/trends?${params}`, { signal });
}

export async function getCostBreakdown({ start, end, groupBy, period } = {}, { signal } = {}) {
  const params = new URLSearchParams();
  if (start) params.set('start_date', start);
  if (end) params.set('end_date', end);
  if (groupBy) params.set('group_by', groupBy);
  if (period) params.set('period', period);
  return fetchApi(`/costs/breakdown?${params}`, { signal });
}

export async function getCostByUser({ start, end, period } = {}, { signal } = {}) {
  const params = new URLSearchParams();
  if (start) params.set('start_date', start);
  if (end) params.set('end_date', end);
  if (period) params.set('period', period);
  return fetchApi(`/costs/by-user?${params}`, { signal });
}

export async function getCostBySource({ start, end, period } = {}, { signal } = {}) {
  const params = new URLSearchParams();
  if (start) params.set('start_date', start);
  if (end) params.set('end_date', end);
  if (period) params.set('period', period);
  return fetchApi(`/costs/by-source?${params}`, { signal });
}

export async function getSourceEstimate({ signal } = {}) {
  return fetchApi('/costs/source-estimate', { signal });
}
