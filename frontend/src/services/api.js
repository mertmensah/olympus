const API_BASE = "http://localhost:8000";
let accessTokenGetter = () => null;

export function setAuthTokenGetter(getter) {
  accessTokenGetter = typeof getter === "function" ? getter : () => null;
}

async function request(path, options = {}) {
  const accessToken = accessTokenGetter();
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
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

export function getJobArtifacts(jobId) {
  return request(`/api/jobs/${jobId}/artifacts`);
}

export function getJobDebug(jobId) {
  return request(`/api/jobs/${jobId}/debug`);
}

export function getJobInputFeedback(jobId) {
  return request(`/api/jobs/${jobId}/input-feedback`);
}

export function getReconstructionFileUrl(jobId) {
  return `${API_BASE}/api/jobs/${jobId}/reconstruction`;
}

export function startJobPipeline(jobId) {
  return request(`/api/jobs/${jobId}/start`, {
    method: "POST"
  });
}

export function listConnections() {
  return request("/api/connections");
}

export function requestConnection(targetUserId) {
  return request("/api/connections/request", {
    method: "POST",
    body: JSON.stringify({ target_user_id: targetUserId })
  });
}

export function acceptConnection(connectionId) {
  return request(`/api/connections/${connectionId}/accept`, {
    method: "POST"
  });
}

export function declineConnection(connectionId) {
  return request(`/api/connections/${connectionId}/decline`, {
    method: "POST"
  });
}
