import React, { useState } from 'react';
import GraphCanvas from './components/GraphCanvas';
import Uploader from './components/Uploader';

export default function App() {
  const [token, setToken] = useState('');
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleRefresh = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  return (
    <>
      <Uploader token={token} setToken={setToken} onUploadComplete={handleRefresh} />
      <GraphCanvas token={token} refreshTrigger={refreshTrigger} />
    </>
  );
}
