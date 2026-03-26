export const API_BASE = 'http://localhost:8000/api';

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

// Automatically loops if the backend is 'processing' in AWS Lambda
export async function getClusters(token, mode = 'combined', timeEps = 60, distEps = 1.0, minSamples = 2) {
  const params = new URLSearchParams({
    mode,
    time_eps_minutes: timeEps,
    distance_eps_km: distEps,
    min_samples: minSamples
  });

  for (let i = 0; i < 10; i++) {
    const res = await fetch(`${API_BASE}/clusters?${params}`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    if (!res.ok) throw new Error(await res.text());
    
    const data = await res.json();
    if (data.status === 'processing') {
      // Wait 3 seconds and poll again
      await new Promise(resolve => setTimeout(resolve, 3000));
      continue;
    }
    return data;
  }
  throw new Error("Lambda cluster processing timed out");
}
