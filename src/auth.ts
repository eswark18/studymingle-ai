export type AuthUser = {
  id: string
  email: string
  display_name: string | null
  education_track: string | null
  grade_or_year: string | null
  email_verified_at: string | null
  created_at: string
}

export type AuthMode = 'login' | 'register'

export type Worksheet = {
  id: string
  original_filename: string
  content_type: string
  size_bytes: number
  sha256: string
  status: string
  created_at: string
}

export type ExtractedQuestion = {
  id: string
  question_number: number
  extracted_text: string
  edited_text: string | null
  confidence: number | null
  page_number: number | null
}

export type OcrJob = {
  id: string
  worksheet_id: string
  status: 'queued' | 'retrying' | 'processing' | 'completed' | 'failed'
  extraction_method: string | null
  error_message: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
  questions: ExtractedQuestion[]
}

const apiBase = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  headers.set('Accept', 'application/json')

  const response = await fetch(`${apiBase}/api/v1${path}`, {
    ...init,
    headers,
    credentials: 'include',
  })

  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null
    throw new ApiError(payload?.detail ?? 'Something went wrong. Please try again.', response.status)
  }

  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export function getCurrentUser() {
  return apiRequest<AuthUser>('/auth/me')
}

export function logout() {
  return apiRequest<void>('/auth/logout', { method: 'POST' })
}

export function uploadWorksheet(file: File) {
  const body = new FormData()
  body.append('file', file)
  return apiRequest<Worksheet>('/worksheets', { method: 'POST', body })
}

export function listWorksheets() {
  return apiRequest<Worksheet[]>('/worksheets')
}

export function deleteWorksheet(id: string) {
  return apiRequest<void>(`/worksheets/${id}`, { method: 'DELETE' })
}

export function getWorksheetDownload(id: string) {
  return apiRequest<{ url: string; expires_in: number }>(`/worksheets/${id}/download`)
}

export function startQuestionExtraction(worksheetId: string) {
  return apiRequest<OcrJob>(`/worksheets/${worksheetId}/extract`, { method: 'POST' })
}

export function getQuestionExtraction(jobId: string) {
  return apiRequest<OcrJob>(`/ocr-jobs/${jobId}`)
}

export function retryQuestionExtraction(jobId: string) {
  return apiRequest<OcrJob>(`/ocr-jobs/${jobId}/retry`, { method: 'POST' })
}

export function updateExtractedQuestion(questionId: string, editedText: string) {
  return apiRequest<ExtractedQuestion>(`/questions/${questionId}`, {
    method: 'PATCH',
    body: JSON.stringify({ text: editedText }),
  })
}
