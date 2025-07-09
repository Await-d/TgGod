import axios from 'axios';
import { ApiResponse, PaginatedResponse } from '../types';

// 创建axios实例
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加token等认证信息
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

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    const message = error.response?.data?.message || error.message || '请求失败';
    return Promise.reject(new Error(message));
  }
);

// 通用API方法
export const apiService = {
  // GET请求
  get: <T>(url: string, params?: any): Promise<ApiResponse<T>> => {
    return api.get(url, { params });
  },

  // POST请求
  post: <T>(url: string, data?: any): Promise<ApiResponse<T>> => {
    return api.post(url, data);
  },

  // PUT请求
  put: <T>(url: string, data?: any): Promise<ApiResponse<T>> => {
    return api.put(url, data);
  },

  // DELETE请求
  delete: <T>(url: string): Promise<ApiResponse<T>> => {
    return api.delete(url);
  },

  // 分页请求
  getPaginated: <T>(url: string, params?: any): Promise<ApiResponse<PaginatedResponse<T>>> => {
    return api.get(url, { params });
  },

  // 文件上传
  uploadFile: (url: string, file: File, onProgress?: (progress: number) => void): Promise<ApiResponse<any>> => {
    const formData = new FormData();
    formData.append('file', file);
    
    return api.post(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });
  },

  // 文件下载
  downloadFile: (url: string, filename: string): Promise<void> => {
    return api.get(url, { responseType: 'blob' }).then((response) => {
      const blob = new Blob([response.data]);
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    });
  },
};

export default api;