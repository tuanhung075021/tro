/*
 * Copyright (c) 2026 tro Contributors
 * SPDX-License-Identifier: MIT
 */

/**
 * REST API client module configured for tro backend services.
 * Base URL defaults to http://localhost:8000/api/v1, automatically attaches
 * JWT Authorization header and provides robust network error handling.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

/**
 * Retrieve the current JWT authentication token from localStorage.
 */
export function getToken() {
  return localStorage.getItem('tro_token') || localStorage.getItem('token');
}

/**
 * Persist the active JWT authentication token to localStorage.
 */
export function setToken(token) {
  if (token) {
    localStorage.setItem('tro_token', token);
    localStorage.setItem('token', token);
  } else {
    localStorage.removeItem('tro_token');
    localStorage.removeItem('token');
  }
}

/**
 * Clear authentication credentials and user profile from localStorage.
 */
export function removeToken() {
  localStorage.removeItem('tro_token');
  localStorage.removeItem('token');
  localStorage.removeItem('tro_user');
}

/**
 * Primary HTTP request wrapper for tro backend API.
 * Handles header injection, query serialization, response status parsing, and error formatting.
 */
export async function request(endpoint, options = {}) {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
  const token = getToken();

  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const config = {
    ...options,
    headers,
  };

  try {
    const response = await fetch(url, config);

    // Parse response body if available
    let data = null;
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      const text = await response.text();
      data = text ? { raw: text } : null;
    }

    if (!response.ok) {
      const errorMessage =
        data?.detail ||
        (Array.isArray(data?.detail)
          ? data.detail.map((e) => e.msg || e).join(', ')
          : null) ||
        data?.message ||
        `Yêu cầu thất bại với mã lỗi ${response.status} (${response.statusText})`;

      const error = new Error(errorMessage);
      error.status = response.status;
      error.data = data;
      throw error;
    }

    return data;
  } catch (err) {
    const msg = (err.message || '').toLowerCase();
    if (
      err.name === 'TypeError' &&
      (msg.includes('fetch') ||
        msg.includes('load') ||
        msg.includes('network') ||
        msg.includes('failed'))
    ) {
      const networkError = new Error(
        'Không thể kết nối đến máy chủ backend (http://localhost:8000). Vui lòng kiểm tra lại dịch vụ.'
      );
      networkError.status = 0;
      throw networkError;
    }
    throw err;
  }
}

// ----------------------------------------------------------------------------
// Authentication API
// ----------------------------------------------------------------------------
export const auth = {
  login: (username, password) =>
    request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  register: (userData) =>
    request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    }),

  getMe: () =>
    request('/auth/me', {
      method: 'GET',
    }),

  removeTenant: (roomId) =>
    request(`/auth/rooms/${roomId}/remove-tenant`, {
      method: 'POST',
    }),
};

// ----------------------------------------------------------------------------
// Properties API (Quản lý Khu trọ)
// ----------------------------------------------------------------------------
export const properties = {
  list: () =>
    request('/properties', {
      method: 'GET',
    }),

  get: (id) =>
    request(`/properties/${id}`, {
      method: 'GET',
    }),

  create: (data) =>
    request('/properties', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getRooms: (propertyId) =>
    request(`/properties/${propertyId}/rooms`, {
      method: 'GET',
    }),

  createRoom: (propertyId, data) =>
    request(`/properties/${propertyId}/rooms`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

// ----------------------------------------------------------------------------
// Rooms & Readings API (Phòng trọ & Chỉ số công tơ)
// ----------------------------------------------------------------------------
export const rooms = {
  get: (id) =>
    request(`/rooms/${id}`, {
      method: 'GET',
    }),

  getReadings: (roomId) =>
    request(`/rooms/${roomId}/readings`, {
      method: 'GET',
    }),

  createReading: (roomId, data) =>
    request(`/rooms/${roomId}/readings`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getInvoices: (roomId) =>
    request(`/rooms/${roomId}/invoices`, {
      method: 'GET',
    }),

  calculateInvoice: (roomId, data) =>
    request(`/rooms/${roomId}/invoices/calculate`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

// ----------------------------------------------------------------------------
// Invoices API (Hóa đơn & Tra cứu công khai Tính năng 17)
// ----------------------------------------------------------------------------
export const invoices = {
  get: (id) =>
    request(`/invoices/${id}`, {
      method: 'GET',
    }),

  getPublic: (shareToken) =>
    request(`/invoices/public/${encodeURIComponent(shareToken)}`, {
      method: 'GET',
    }),
};

// ----------------------------------------------------------------------------
// System Pricing Configuration API (/config)
// ----------------------------------------------------------------------------
export const systemConfig = {
  get: () =>
    request('/config', {
      method: 'GET',
    }),

  update: (data) =>
    request('/config', {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
};

export default {
  request,
  getToken,
  setToken,
  removeToken,
  auth,
  properties,
  rooms,
  invoices,
  systemConfig,
};
