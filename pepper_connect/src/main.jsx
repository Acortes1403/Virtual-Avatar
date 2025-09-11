import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import Prueba from './Prueba.jsx'
import { installVhFix } from './vh-fix.jsx'
import './polyfills'

installVhFix()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Prueba />
  </StrictMode>,
)
