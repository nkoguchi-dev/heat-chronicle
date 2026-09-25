import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import '@/app/globals.css';
import '@/vite-fonts.css';

import { App } from '@/App';

const rootElement = document.getElementById('root');

if (rootElement === null) {
  throw new Error('Application root element was not found');
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
