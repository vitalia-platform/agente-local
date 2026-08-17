import axios from 'axios';

// Base API Configuration
export const apiClient = axios.create({
  baseURL: import.meta.env.DEV ? 'http://localhost:8000/api' : '/api',
  timeout: 10000,
});

// Request Interceptor to inject JWT
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('vitalia_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

// Response Interceptor for global errors (e.g. 401)
apiClient.interceptors.response.use((response) => response, (error) => {
  if (error.response && error.response.status === 401) {
    localStorage.removeItem('vitalia_token');
    window.location.href = '/login';
  }
  return Promise.reject(error);
});
