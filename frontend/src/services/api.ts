const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

async function fetchApi(endpoint: string, options: RequestInit = {}): Promise<Response> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  // Add user email header if available (fallback for mobile Safari cookie issues)
  const userEmail = localStorage.getItem('centi_user_email');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...options.headers as Record<string, string>,
  };
  
  // Add user email as header if available (backend can use this as fallback)
  if (userEmail && !headers['X-User-Email']) {
    headers['X-User-Email'] = userEmail;
  }
  
  const response = await fetch(url, {
    ...options,
    credentials: 'include', // Include cookies
    headers,
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `HTTP error! status: ${response.status}`);
  }
  
  return response;
}

export const api = {
  async get<T>(endpoint: string): Promise<T> {
    const response = await fetchApi(endpoint);
    return response.json();
  },
  
  async post<T>(endpoint: string, data?: any): Promise<T> {
    const response = await fetchApi(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
    return response.json();
  },
  
  async delete<T>(endpoint: string): Promise<T> {
    const response = await fetchApi(endpoint, {
      method: 'DELETE',
    });
    return response.json();
  },
};

