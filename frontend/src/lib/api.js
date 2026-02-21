import axios from 'axios';
import Cookies from 'js-cookie';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const api = axios.create({
  baseURL: `${BACKEND_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = Cookies.get('zomoto_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      Cookies.remove('zomoto_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Helper function to extract error message from API errors
export const getErrorMessage = (error, defaultMessage = 'An error occurred') => {
  const errorDetail = error.response?.data?.detail;
  
  if (Array.isArray(errorDetail)) {
    // Handle Pydantic validation errors (array of error objects)
    return errorDetail.map(e => e.msg || e.message || 'Validation error').join(', ');
  } else if (typeof errorDetail === 'string') {
    return errorDetail;
  } else if (typeof errorDetail === 'object' && errorDetail?.msg) {
    return errorDetail.msg;
  }
  
  return error.message || defaultMessage;
};

export default api;
