export const config = {
    apiBaseUrl: import.meta.env.VITE_API_URL || 'http://localhost:8080/api/v1',
    timeouts: {
        upload: 0, // No timeout
        default: 10000,
    },
};
