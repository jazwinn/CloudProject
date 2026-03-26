import React, { useState } from 'react';
import { uploadPhoto } from '../api';

export default function Uploader({ token, setToken, onUploadComplete }) {
  const [isOpen, setIsOpen] = useState(false);
  const [files, setFiles] = useState([]);
  const [status, setStatus] = useState('');

  const handleUpload = async () => {
    if (!token) {
      setStatus('Please enter your Cognito Token first.');
      return;
    }
    if (files.length === 0) return;

    setStatus('Uploading...');
    let successCount = 0;
    for (let i = 0; i < files.length; i++) {
        try {
            await uploadPhoto(token, files[i]);
            successCount++;
            setStatus(`Uploaded ${successCount}/${files.length}...`);
        } catch (e) {
            console.error('Upload failed:', e);
        }
    }
    setStatus(`Done! Uploaded ${successCount} photos.`);
    if (successCount > 0 && onUploadComplete) {
        onUploadComplete();
    }
  };

  return (
    <div style={{ position: 'fixed', top: 20, right: 20, zIndex: 1000, background: 'rgba(20,20,20,0.9)', padding: 15, borderRadius: 8, color: 'white', border: '1px solid #333' }}>
      <button onClick={() => setIsOpen(!isOpen)} style={{ background: '#333', color: 'white', border: 'none', padding: '5px 10px', borderRadius: 4, cursor: 'pointer' }}>
        {isOpen ? 'Close Data Panel' : 'Data Panel'}
      </button>

      {isOpen && (
        <div style={{ marginTop: 15, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <input 
            type="password" 
            placeholder="Cognito Auth Token" 
            value={token || ''}
            onChange={e => setToken(e.target.value)}
            style={{ padding: 6, borderRadius: 4, border: '1px solid #555', background: '#222', color: 'white' }}
          />
          <input 
            type="file" 
            multiple 
            accept="image/*" 
            onChange={e => setFiles(e.target.files)}
            style={{ padding: 6 }}
          />
          <button onClick={handleUpload} style={{ background: '#5DCAA5', color: '#000', border: 'none', padding: 8, borderRadius: 4, fontWeight: 'bold', cursor: 'pointer' }}>
            Upload Photos
          </button>
          
          <button onClick={onUploadComplete} style={{ background: '#85B7EB', color: '#000', border: 'none', padding: 8, borderRadius: 4, fontWeight: 'bold', cursor: 'pointer' }}>
            Refresh Graph
          </button>
          {status && <div style={{ fontSize: '0.85em', color: '#aaa' }}>{status}</div>}
        </div>
      )}
    </div>
  );
}
