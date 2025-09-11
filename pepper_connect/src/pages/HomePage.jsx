import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function HomePage() {
  const [isLoaded, setIsLoaded] = useState(false);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const navigate = useNavigate();

  useEffect(() => {
    setIsLoaded(true);
  }, []);

  useEffect(() => {
    const handleMouseMove = (e) => {
      setMousePosition({
        x: (e.clientX / window.innerWidth) * 100,
        y: (e.clientY / window.innerHeight) * 100
      });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return (
    <div
      className="fixed top-0 left-0 w-screen h-screen bg-cover bg-center bg-no-repeat flex items-center justify-center relative overflow-hidden z-0"
      style={{ 
        backgroundImage: `linear-gradient(135deg, #667eea 0%, #764ba2 100%)`,
        backgroundSize: 'cover',
        margin: '0 !important',
        padding: '0 !important',
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0
      }}
    >
      {/* Overlay con gradiente dinámico */}
      <div 
        className="absolute inset-0 transition-all duration-1000"
        style={{
          background: `radial-gradient(circle at ${mousePosition.x}% ${mousePosition.y}%, rgba(99, 102, 241, 0.4) 0%, rgba(139, 92, 246, 0.3) 30%, rgba(59, 130, 246, 0.2) 70%, transparent 100%)`
        }}
      />
      
      {/* Partículas flotantes */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(20)].map((_, i) => (
          <div
            key={i}
            className="absolute w-2 h-2 bg-white/30 rounded-full"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animation: `float ${3 + Math.random() * 4}s ease-in-out infinite`,
              animationDelay: `${Math.random() * 3}s`
            }}
          />
        ))}
      </div>

      {/* Contenido principal */}
      <div 
        className={`relative z-10 transform transition-all duration-1000 ease-out ${
          isLoaded ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0'
        }`}
      >
        {/* Card principal con glassmorphism */}
        <div className="backdrop-blur-xl bg-white/10 border border-white/20 px-10 py-8 rounded-3xl text-center max-w-lg text-white shadow-2xl hover:shadow-purple-500/20 transition-all duration-500 hover:scale-105 hover:bg-white/15 hover:border-white/30">
          
          {/* Avatar icon animado */}
          <div className="mb-6 relative">
            <div 
              className="w-24 h-24 mx-auto bg-gradient-to-r from-indigo-500 to-purple-600 rounded-full flex items-center justify-center shadow-2xl transition-all duration-300 hover:shadow-purple-500/50"
              style={{
                animation: 'pulse 2s ease-in-out infinite'
              }}
            >
              <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center backdrop-blur-sm">
                <svg className="w-10 h-10 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2C13.1 2 14 2.9 14 4C14 5.1 13.1 6 12 6C10.9 6 10 5.1 10 4C10 2.9 10.9 2 12 2ZM21 9V7L15 4.5V6C15 7.1 14.1 8 13 8H11C9.9 8 9 7.1 9 6V4.5L3 7V9H21ZM12 12C8.69 12 6 14.69 6 18V20H18V18C18 14.69 15.31 12 12 12Z"/>
                </svg>
              </div>
            </div>
            {/* Anillos animados alrededor del avatar */}
            <div 
              className="absolute inset-0 rounded-full border-2 border-white/30"
              style={{ animation: 'ping 2s cubic-bezier(0, 0, 0.2, 1) infinite' }}
            ></div>
            <div 
              className="absolute inset-2 rounded-full border border-white/20"
              style={{ animation: 'ping 2s cubic-bezier(0, 0, 0.2, 1) infinite', animationDelay: '0.3s' }}
            ></div>
          </div>

          {/* Título con gradiente y animación */}
          <div className="mb-6">
            <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-white via-blue-100 to-purple-100 bg-clip-text text-transparent leading-tight">
              Hola, soy tu Avatar Virtual
            </h1>
            <div 
              className="text-2xl font-light text-indigo-300 transform transition-all duration-700"
              style={{
                animation: 'fadeInUp 1s ease-out 0.5s both'
              }}
            >
              Pepper
            </div>
          </div>
          
          {/* Descripción mejorada */}
          <div 
            className="mb-8 transform transition-all duration-700"
            style={{
              animation: 'fadeInUp 1s ease-out 0.7s both'
            }}
          >
            <p className="text-lg text-blue-100 leading-relaxed font-light mb-4">
              Creo interacciones con IA para robots humanoides como Pepper.
            </p>
            
            {/* Features con iconos */}
            <div className="flex justify-center items-center gap-4 text-sm text-white/80 mb-4">
              <div className="flex items-center gap-1">
                <span className="text-yellow-300">✨</span>
                <span>Experiencias inmersivas</span>
              </div>
              <div className="w-1 h-1 bg-white/40 rounded-full"></div>
              <div className="flex items-center gap-1">
                <span className="text-blue-300">🤖</span>
                <span>IA Avanzada</span>
              </div>
            </div>
            
            <div className="flex justify-center items-center gap-4 text-sm text-white/80">
              <div className="flex items-center gap-1">
                <span className="text-purple-300">💫</span>
                <span>Conexión Humana</span>
              </div>
              <div className="w-1 h-1 bg-white/40 rounded-full"></div>
              <div className="flex items-center gap-1">
                <span className="text-green-300">🚀</span>
                <span>Tecnología del Futuro</span>
              </div>
            </div>
          </div>
          
          {/* Botón mejorado con efectos */}
          <div 
            className="transform transition-all duration-700"
            style={{
              animation: 'fadeInUp 1s ease-out 0.9s both'
            }}
          >
            <button
              onClick={() => navigate("/connect")}
              className="group relative bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-semibold py-4 px-8 rounded-full transition-all duration-300 transform hover:scale-105 focus:outline-none focus:ring-4 focus:ring-purple-500/50 shadow-lg hover:shadow-purple-500/30 overflow-hidden"
            >
              {/* Efecto de brillo animado */}
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent transform -skew-x-12 -translate-x-full group-hover:translate-x-full transition-transform duration-1000"></div>
              
              <span className="relative z-10 flex items-center justify-center gap-2">
                Conectar con Pepper
                <svg className="w-5 h-5 group-hover:translate-x-1 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </span>
            </button>
          </div>

          {/* Indicadores de estado */}
          <div 
            className="mt-8 flex justify-center items-center gap-6 text-sm transform transition-all duration-700"
            style={{
              animation: 'fadeInUp 1s ease-out 1.1s both'
            }}
          >
            <div className="flex items-center gap-2 text-green-300">
              <div 
                className="w-2 h-2 bg-green-400 rounded-full"
                style={{ animation: 'pulse 2s ease-in-out infinite' }}
              ></div>
              Sistema Activo
            </div>
            <div className="flex items-center gap-2 text-blue-300">
              <div 
                className="w-2 h-2 bg-blue-400 rounded-full"
                style={{ animation: 'pulse 2s ease-in-out infinite', animationDelay: '0.5s' }}
              ></div>
              IA Conectada
            </div>
          </div>
        </div>

        {/* Elementos decorativos flotantes */}
        <div className="absolute -top-4 -left-4 w-20 h-20 bg-gradient-to-r from-purple-500/30 to-pink-500/30 rounded-full blur-xl opacity-70" style={{ animation: 'pulse 3s ease-in-out infinite' }}></div>
        <div className="absolute -bottom-6 -right-6 w-16 h-16 bg-gradient-to-r from-blue-500/30 to-indigo-500/30 rounded-full blur-xl opacity-70" style={{ animation: 'pulse 3s ease-in-out infinite', animationDelay: '1s' }}></div>
      </div>

      {/* Información de versión */}
      <div className="absolute bottom-8 left-8 text-white/40 text-sm font-light">
        <div className="flex items-center gap-2">
          <div 
            className="w-1 h-1 bg-white/60 rounded-full"
            style={{ animation: 'pulse 2s ease-in-out infinite' }}
          ></div>
          Pepper Virtual Assistant v2.0
        </div>
      </div>

      {/* CSS personalizado para animaciones y reset */}
      <style>{`
        /* Reset completo para evitar espacios */
        * {
          box-sizing: border-box;
        }
        
        body, html {
          margin: 0 !important;
          padding: 0 !important;
          width: 100% !important;
          height: 100% !important;
          overflow-x: hidden !important;
        }
        
        #root, [data-reactroot] {
          margin: 0 !important;
          padding: 0 !important;
          width: 100% !important;
          min-height: 100vh !important;
        }
        @keyframes float {
          0%, 100% { 
            transform: translateY(0px); 
          }
          50% { 
            transform: translateY(-10px); 
          }
        }
        
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(30px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        @keyframes ping {
          75%, 100% {
            transform: scale(2);
            opacity: 0;
          }
        }
        
        @keyframes pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: .7;
          }
        }
        
        .hover\\:shadow-purple-500\\/20:hover {
          box-shadow: 0 25px 50px -12px rgba(168, 85, 247, 0.2);
        }
        
        .hover\\:shadow-purple-500\\/30:hover {
          box-shadow: 0 20px 40px -12px rgba(168, 85, 247, 0.3);
        }
      `}</style>
    </div>
  );
}