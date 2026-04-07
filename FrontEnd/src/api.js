export const API_BASE = import.meta.env.VITE_API_BASE;

export async function uploadPhoto(token, file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

/**
 * Gets presigned S3 PUT URLs for a batch of files.
 */
export async function getBatchPresignedUrls(token, files) {
  const res = await fetch(`${API_BASE}/upload/batch-presign`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      files: files.map(f => ({
        filename: f.name,
        content_type: f.type
      }))
    })
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json(); // { uploads: [{ filename, file_key, presigned_url }] }
}

/**
 * Uploads a file directly to S3 using a presigned PUT URL.
 */
export async function uploadToS3(presignedUrl, file) {
  const res = await fetch(presignedUrl, {
    method: 'PUT',
    headers: {
      'Content-Type': file.type
    },
    body: file
  });
  if (!res.ok) throw new Error(`S3 Upload failed: ${res.statusText}`);
  return true;
}

export async function getGraph(token, timeEps = 120, distEps = 5.0) {
  const params = new URLSearchParams({
    time_threshold_minutes: timeEps,
    distance_threshold_km: distEps
  });
  const res = await fetch(`${API_BASE}/graph?${params}`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getImageUrl(token, imageId) {
  const res = await fetch(`${API_BASE}/image/${imageId}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json(); // { presigned_url: "..." }
}

// Automatically loops if the backend is 'processing' in AWS Lambda
export async function getClusters(token, mode = 'combined', timeEps = 60, distEps = 1.0, minSamples = 2) {
  const params = new URLSearchParams({
    mode,
    time_eps_minutes: timeEps,
    distance_eps_km: distEps,
    min_samples: minSamples
  });

  const res = await fetch(`${API_BASE}/clusters?${params}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();

}
