export const API_BASE = import.meta.env.API_BASE || "http://CloudGraphLoadBalancer-1678551671.us-east-1.elb.amazonaws.com/api";

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
