/**
 * bulkUpload.js
 * Utility for uploading large batches of photos directly to S3 via presigned PUT URLs.
 *
 * Flow:
 *   1. Call POST /api/upload/batch-presign once with all filenames → receive presigned PUT URLs.
 *   2. Upload files directly to S3 in parallel batches of 20 using Promise.allSettled.
 *      (Promise.allSettled is used — not Promise.all — so a single failure never aborts the batch.)
 *   3. Report progress after each sub-batch via the onProgress callback.
 *   4. Return { succeeded: [...], failed: [...] } for the caller to surface to the user.
 */

const BATCH_SIZE = 20;

/**
 * Uploads an array of File objects directly to S3 using presigned PUT URLs.
 *
 * @param {File[]} files - Array of File objects selected by the user.
 * @param {string} authToken - Cognito JWT bearer token for the batch-presign API call.
 * @param {function({ completed: number, total: number, failed: number }): void} onProgress
 *   - Called after each sub-batch of uploads completes.
 * @param {string} [apiBase='/api'] - Base URL of the CloudGraph API.
 *
 * @returns {Promise<{ succeeded: string[], failed: string[] }>}
 *   succeeded: list of file names that were uploaded successfully.
 *   failed:    list of file names that failed at any stage (presign or upload).
 */
export async function bulkUpload(files, authToken, onProgress, apiBase = '/api') {
  const total = files.length;
  let completed = 0;
  let failedCount = 0;

  if (total === 0) {
    return { succeeded: [], failed: [] };
  }

  // ── Step 1: Request presigned PUT URLs for all files in one API call ──────
  const presignPayload = {
    files: Array.from(files).map((f) => ({
      filename: f.name,
      content_type: f.type || 'image/jpeg',
    })),
  };

  let presignData;
  try {
    const presignResponse = await fetch(`${apiBase}/upload/batch-presign`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${authToken}`,
      },
      body: JSON.stringify(presignPayload),
    });

    if (!presignResponse.ok) {
      const errorText = await presignResponse.text();
      throw new Error(`batch-presign failed (${presignResponse.status}): ${errorText}`);
    }

    presignData = await presignResponse.json();
  } catch (err) {
    // If the presign call itself fails, all files are considered failed
    console.error('[bulkUpload] Presign request failed:', err);
    return {
      succeeded: [],
      failed: Array.from(files).map((f) => f.name),
    };
  }

  // Build a map from filename → { presigned_url, file_key } for easy lookup
  const urlMap = new Map();
  for (const item of presignData.uploads) {
    urlMap.set(item.filename, item);
  }

  // ── Step 2: Upload files directly to S3 in parallel sub-batches of 20 ────
  const succeeded = [];
  const failed = [];

  const fileArray = Array.from(files);

  for (let i = 0; i < fileArray.length; i += BATCH_SIZE) {
    const chunk = fileArray.slice(i, i + BATCH_SIZE);

    const uploadPromises = chunk.map(async (file) => {
      const presignItem = urlMap.get(file.name);
      if (!presignItem) {
        console.warn(`[bulkUpload] No presigned URL found for: ${file.name}`);
        return { status: 'rejected', file };
      }

      const uploadResponse = await fetch(presignItem.presigned_url, {
        method: 'PUT',
        headers: { 'Content-Type': file.type || 'image/jpeg' },
        body: file,
      });

      if (!uploadResponse.ok) {
        throw new Error(`S3 PUT returned ${uploadResponse.status} for ${file.name}`);
      }

      return { status: 'fulfilled', file, fileKey: presignItem.file_key };
    });

    // Promise.allSettled ensures partial failures don't abort the batch
    const results = await Promise.allSettled(uploadPromises);

    for (const result of results) {
      if (result.status === 'fulfilled' && result.value?.status !== 'rejected') {
        succeeded.push(result.value.file.name);
        completed++;
      } else {
        const fileName =
          result.status === 'rejected'
            ? chunk[results.indexOf(result)]?.name ?? 'unknown'
            : result.value?.file?.name ?? 'unknown';
        console.error('[bulkUpload] Upload failed:', fileName, result.reason ?? result.value);
        failed.push(fileName);
        failedCount++;
        completed++;
      }
    }

    // ── Step 3: Report progress after each sub-batch ──────────────────────
    if (typeof onProgress === 'function') {
      onProgress({ completed, total, failed: failedCount });
    }
  }

  return { succeeded, failed };
}
