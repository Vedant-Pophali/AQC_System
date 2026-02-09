import axios, { AxiosInstance, AxiosError } from 'axios';
import { config } from '../config';

const apiClient: AxiosInstance = axios.create({
    baseURL: config.apiBaseUrl,
    timeout: config.timeouts.upload, // 0 means no timeout
    headers: {
        'Content-Type': 'application/json',
    },
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
        // Handle specific error cases (e.g. 401, 500)
        // const message = (error.response?.data as any)?.message || 'An unexpected error occurred';
        // console.error('API Error:', message);
        return Promise.reject(error);
    }
);

export default apiClient;
