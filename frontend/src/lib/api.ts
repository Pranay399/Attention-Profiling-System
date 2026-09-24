/**
 * API client for the Attention Profiling System backend.
 *
 * Centralized HTTP client with:
 * - Automatic token management
 * - Consistent error handling
 * - Type-safe request/response
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

/** Stored auth token. In production, use httpOnly cookies. */
let authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
  if (token) {
    if (typeof window !== 'undefined') localStorage.setItem('aps_token', token);
  } else {
    if (typeof window !== 'undefined') localStorage.removeItem('aps_token');
  }
}

export function getAuthToken(): string | null {
  if (authToken) return authToken;
  if (typeof window !== 'undefined') {
    authToken = localStorage.getItem('aps_token');
  }
  return authToken;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Don't set Content-Type for FormData (browser sets it with boundary)
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMessage = 'An unexpected error occurred';
    let errorCode = 'UNKNOWN';
    try {
      const errorBody = await response.json();
      errorMessage = errorBody.error?.message || errorMessage;
      errorCode = errorBody.error?.code || errorCode;
    } catch {
      // Response wasn't JSON
    }

    if (response.status === 401) {
      setAuthToken(null);
    }

    throw new ApiError(response.status, errorCode, errorMessage);
  }

  return response.json();
}

// ── Auth ──────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export const auth = {
  register: (data: { email: string; password: string; full_name: string; role?: string }) =>
    request<User>('/auth/register', { method: 'POST', body: JSON.stringify(data) }),

  login: (data: { email: string; password: string }) =>
    request<TokenResponse>('/auth/login', { method: 'POST', body: JSON.stringify(data) }),

  me: () => request<User>('/auth/me'),
};

// ── Courses ──────────────────────────────────────────────────────────────

export interface Course {
  id: string;
  name: string;
  code: string;
  description: string | null;
  instructor_id: string;
  created_at: string;
}

export interface CourseDetail extends Course {
  instructor: User;
  session_count: number;
}

export const courses = {
  list: () => request<Course[]>('/courses'),
  get: (id: string) => request<CourseDetail>(`/courses/${id}`),
  create: (data: { name: string; code: string; description?: string }) =>
    request<Course>('/courses', { method: 'POST', body: JSON.stringify(data) }),
};

// ── Sessions ─────────────────────────────────────────────────────────────

export interface Session {
  id: string;
  course_id: string;
  title: string;
  description: string | null;
  session_date: string;
  created_by: string;
  created_at: string;
}

export interface SessionDetail extends Session {
  recordings: Recording[];
}

export const sessions = {
  list: (courseId: string) => request<Session[]>(`/courses/${courseId}/sessions`),
  get: (id: string) => request<SessionDetail>(`/sessions/${id}`),
  create: (courseId: string, data: { title: string; description?: string; session_date: string }) =>
    request<Session>(`/courses/${courseId}/sessions`, { method: 'POST', body: JSON.stringify(data) }),
};

// ── Recordings ───────────────────────────────────────────────────────────

export interface Recording {
  id: string;
  session_id: string;
  filename: string;
  file_size_bytes: number | null;
  duration_seconds: number | null;
  status: 'uploaded' | 'processing' | 'completed' | 'failed';
  error_message: string | null;
  uploaded_by: string;
  created_at: string;
}

export const recordings = {
  get: (id: string) => request<Recording>(`/recordings/${id}`),
  upload: (sessionId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return request<Recording>(`/sessions/${sessionId}/recordings/upload`, {
      method: 'POST',
      body: formData,
    });
  },
  analyze: (id: string) =>
    request<AnalysisJob>(`/recordings/${id}/analyze`, { method: 'POST' }),
  streamUrl: (id: string) => `${API_BASE}/recordings/${id}/stream`,
};

// ── Analysis ─────────────────────────────────────────────────────────────

export interface AnalysisJob {
  id: string;
  recording_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  model_version: string;
  frames_total: number | null;
  frames_processed: number | null;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  created_at: string;
}

export interface Participant {
  id: string;
  label: string;
  student_id: string | null;
  first_seen_sec: number | null;
  last_seen_sec: number | null;
  frame_count: number;
}

export interface Observation {
  id: string;
  participant_id: string;
  timestamp_sec: number;
  frame_number: number;
  behavior: string;
  head_yaw: number | null;
  head_pitch: number | null;
  head_roll: number | null;
  confidence: number | null;
}

export interface BehaviorCount {
  behavior: string;
  count: number;
  percentage: number;
}

export interface ParticipantSummary {
  participant_id: string;
  label: string;
  total_observations: number;
  behavior_breakdown: BehaviorCount[];
  avg_confidence: number | null;
}

export interface AnalysisSummary {
  analysis_id: string;
  total_participants: number;
  total_observations: number;
  duration_seconds: number | null;
  overall_behavior_distribution: BehaviorCount[];
  participant_summaries: ParticipantSummary[];
}

export interface TimelineBucket {
  timestamp_sec: number;
  participant_id: string;
  label: string;
  behavior: string;
  count: number;
}

export const analysis = {
  get: (id: string) => request<AnalysisJob>(`/analysis/${id}`),
  participants: (id: string) => request<Participant[]>(`/analysis/${id}/participants`),
  timeline: (id: string, bucketSeconds = 5) =>
    request<TimelineBucket[]>(`/analysis/${id}/timeline?bucket_seconds=${bucketSeconds}`),
  observations: (id: string, participantId?: string, limit = 1000, offset = 0) => {
    let path = `/analysis/${id}/observations?limit=${limit}&offset=${offset}`;
    if (participantId) path += `&participant_id=${participantId}`;
    return request<Observation[]>(path);
  },
  summary: (id: string) => request<AnalysisSummary>(`/analysis/${id}/summary`),
};
