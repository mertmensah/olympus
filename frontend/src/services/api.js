const API_BASE = "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Request failed");
  }

  return response.json();
}

export function createJob(payload) {
  return request("/api/jobs", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getJobStatus(jobId) {
  return request(`/api/jobs/${jobId}`);
}

export function getJobRecord(jobId) {
  return request(`/api/jobs/${jobId}/record`);
}

export function createUploadSession(jobId, files) {
  return request(`/api/jobs/${jobId}/upload-session`, {
    method: "POST",
    body: JSON.stringify({ files })
  });
}

export async function uploadToTarget(target, file) {
  const response = await fetch(target.upload_url, {
    method: target.method || "PUT",
    headers: {
      "Content-Type": file.type || "application/octet-stream"
    },
    body: file
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || `Upload failed for ${file.name}`);
  }

  return response.json();
}

export function getJobAssets(jobId) {
  return request(`/api/jobs/${jobId}/assets`);
}
