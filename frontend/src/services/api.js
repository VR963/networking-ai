import axios from 'axios';

// Base API URL - adjust based on your environment
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear token and redirect to login
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  register: (userData) => apiClient.post('/auth/register', userData),
  login: (credentials) => apiClient.post('/auth/login', credentials),
  logout: () => apiClient.post('/auth/logout'),
  getProfile: () => apiClient.get('/auth/me'),
};

// User API
export const userAPI = {
  getProfile: (userId) => apiClient.get(`/users/${userId}`),
  updateProfile: (userId, data) => apiClient.put(`/users/${userId}`, data),
  uploadResume: (userId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post(`/users/${userId}/resume`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

// Job API
export const jobAPI = {
  getAllJobs: (params) => apiClient.get('/jobs', { params }),
  getJob: (jobId) => apiClient.get(`/jobs/${jobId}`),
  createJob: (jobData) => apiClient.post('/jobs', jobData),
  updateJob: (jobId, jobData) => apiClient.put(`/jobs/${jobId}`, jobData),
  deleteJob: (jobId) => apiClient.delete(`/jobs/${jobId}`),
  searchJobs: (query) => apiClient.get('/jobs/search', { params: { q: query } }),
};

// Matching API
export const matchingAPI = {
  getMatches: (userId) => apiClient.get(`/users/${userId}/matches`),
  getMatchDetails: (matchId) => apiClient.get(`/matches/${matchId}`),
  acceptMatch: (matchId) => apiClient.post(`/matches/${matchId}/accept`),
  rejectMatch: (matchId) => apiClient.post(`/matches/${matchId}/reject`),
  requestMatching: (userId) => apiClient.post(`/users/${userId}/match`),
};

// Agent API
export const agentAPI = {
  getAgents: () => apiClient.get('/agents'),
  getAgent: (agentId) => apiClient.get(`/agents/${agentId}`),
  chatWithAgent: (agentId, message) =>
    apiClient.post(`/agents/${agentId}/chat`, { message }),
  getConversationHistory: (agentId, userId) =>
    apiClient.get(`/agents/${agentId}/conversations/${userId}`),
};

// Interview API
export const interviewAPI = {
  startInterview: (userId) => apiClient.post(`/users/${userId}/interview/start`),
  submitAnswer: (interviewId, questionId, answer) =>
    apiClient.post(`/interviews/${interviewId}/answers`, { questionId, answer }),
  getInterviewStatus: (interviewId) => apiClient.get(`/interviews/${interviewId}`),
};

// Company API
export const companyAPI = {
  getCompany: (companyId) => apiClient.get(`/companies/${companyId}`),
  updateCompany: (companyId, data) => apiClient.put(`/companies/${companyId}`, data),
  getCompanyJobs: (companyId) => apiClient.get(`/companies/${companyId}/jobs`),
  getCandidates: (companyId, jobId) =>
    apiClient.get(`/companies/${companyId}/jobs/${jobId}/candidates`),
};

// Notifications API
export const notificationAPI = {
  getNotifications: (userId) => apiClient.get(`/users/${userId}/notifications`),
  markAsRead: (notificationId) => apiClient.put(`/notifications/${notificationId}/read`),
  markAllAsRead: (userId) => apiClient.put(`/users/${userId}/notifications/read-all`),
};

export default apiClient;
