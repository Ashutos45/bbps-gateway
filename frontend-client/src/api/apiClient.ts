import axios from 'axios';
import { canonicalize, calculateHmacSha256, generateNonce } from '../utils/crypto';
import { useAuthStore } from '../state/authStore';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 15000,
  // Do not parse JSON automatically to preserve the exact raw response body string for signature verification
  transformResponse: [(data) => data],
});

// Request Interceptor: Inject HMAC headers and canonicalize request body
apiClient.interceptors.request.use(
  async (config) => {
    const timestamp = Math.floor(Date.now() / 1000).toString();
    const nonce = generateNonce();
    const traceId = `trace-${generateNonce().substring(0, 8)}`;

    let canonicalBody = '';
    
    // Canonicalize body only for POST, PUT, PATCH requests with data
    if (config.data && (config.method === 'post' || config.method === 'put' || config.method === 'patch')) {
      canonicalBody = canonicalize(config.data);
      // Re-assign the config data as the parsed JSON of canonicalized string
      // so the wire bytes match the signed format exactly.
      config.data = JSON.parse(canonicalBody);
    }

    const secret = import.meta.env.VITE_CLIENT_SECRET || '';
    const payload = canonicalBody + timestamp + nonce;
    const signature = (await calculateHmacSha256(payload, secret)).toUpperCase();

    config.headers['X-Timestamp'] = timestamp;
    config.headers['X-Nonce'] = nonce;
    config.headers['X-Signature'] = signature;
    config.headers['X-Trace-Id'] = traceId;

    // Inject active authentication credentials
    const { apiKey, jwtToken } = useAuthStore.getState();
    if (jwtToken) {
      config.headers['Authorization'] = `Bearer ${jwtToken}`;
    } else if (apiKey) {
      config.headers['X-API-Key'] = apiKey;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response Interceptor: Validate response signature and parse JSON
apiClient.interceptors.response.use(
  async (response) => {
    const responseSignature = response.headers['x-response-signature'] || response.headers['X-Response-Signature'];
    const rawBody = response.data;

    if (responseSignature && rawBody) {
      const secret = import.meta.env.VITE_CLIENT_SECRET || '';
      const calculated = (await calculateHmacSha256(rawBody, secret)).toUpperCase();
      if (calculated !== responseSignature.toUpperCase()) {
        console.error(`Response signature verification failed. Calculated: ${calculated} vs Header: ${responseSignature}`);
        throw new Error('Response signature verification failed. The payload integrity is compromised.');
      }
    }

    // Safely parse JSON from rawBody
    const contentType = String(response.headers['content-type'] || '');
    if (contentType.includes('application/json') && typeof rawBody === 'string') {
      try {
        if (rawBody.trim() !== '') {
          response.data = JSON.parse(rawBody);
        }
      } catch (err) {
        console.error('Error parsing response JSON data', err);
      }
    }

    return response;
  },
  (error) => {
    // If the error response contains data as raw string, parse it to JSON
    if (error.response && error.response.data && typeof error.response.data === 'string') {
      const contentType = String(error.response.headers['content-type'] || '');
      if (contentType.includes('application/json')) {
        try {
          error.response.data = JSON.parse(error.response.data);
        } catch (err) {}
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;
