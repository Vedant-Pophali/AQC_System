import axios from 'axios';

// Create a configured axios instance
const apiClient = axios.create({
    baseURL: 'http://localhost:8080/api/v1',
    timeout: 30000,
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
