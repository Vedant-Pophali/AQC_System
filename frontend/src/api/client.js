import axios from 'axios';

// Create a configured axios instance
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080/api/v1';

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    timeout: 0, // No timeout for large uploads
    headers: {
        'Content-Type': 'application/json',
    },
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        // Handle specific error cases (e.g. 401, 500)
        const message = error.response?.data?.message || 'An unexpected error occurred';
        console.error('API Error:', message);
        return Promise.reject(error);
    }
);

export default apiClient;
