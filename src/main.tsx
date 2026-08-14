import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import ProductionGate from './components/ProductionGate.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ProductionGate>
      <App />
    </ProductionGate>
  </StrictMode>,
)
