// 📄 src/index.js
import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

const container = document.getElementById('root');
const root = createRoot(container);
root.render(<App />);
// 백엔드 연결 테스트
fetch('http://localhost:8000/health')
  .then(res => res.json())
  .then(data => console.log('백엔드 연결 성공:', data))
  .catch(err => console.error('백엔드 연결 실패:', err));