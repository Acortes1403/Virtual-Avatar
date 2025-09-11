import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function ConnectPage() {
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    pepperIP: '',
    pepperPassword: ''
  });
  const [isLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const navigate = useNavigate();

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Limpiar error del campo cuando el usuario empiece a escribir
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

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
      {/* Overlay con gradiente */}
      <div className="absolute inset-0 bg-gradient-to-br from-purple-900/80 via-blue-900/70 to-indigo-900/80" />
      
      {/* Partículas flotantes */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(15)].map((_, i) => (
          <div
            key={i}
            className="absolute w-2 h-2 bg-white/20 rounded-full"
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
      <div className="relative z-10 w-full max-w-md mx-4">
        
        {/* Botón de regreso */}
        <button
          onClick={() => navigate("/")}
          className="mb-6 flex items-center gap-2 text-white/80 hover:text-white transition-all duration-300 group"
        >
          <svg className="w-5 h-5 group-hover:-translate-x-1 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Volver al inicio
        </button>

        {/* Card principal del formulario */}
        <div className="backdrop-blur-xl bg-white/10 border border-white/20 px-8 py-8 rounded-3xl text-white shadow-2xl hover:shadow-purple-500/20 transition-all duration-500 hover:bg-white/15">
          
          {/* Header */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold mb-2 bg-gradient-to-r from-white to-blue-100 bg-clip-text text-transparent">
              Conectar con Pepper
            </h2>
            <p className="text-blue-100/80 text-sm">
              Ingresa tus datos y la información de conexión
            </p>
          </div>

          {/* Formulario */}
          <div className="space-y-6">
            
            {/* Información Personal */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-blue-100 border-b border-white/20 pb-2">
                👤 Información Personal
              </h3>
              
              <div className="grid grid-cols-2 gap-4">
                {/* Nombre */}
                <div>
                  <label className="block text-sm font-medium text-blue-100 mb-2">
                    Nombre *
                  </label>
                  <input
                    type="text"
                    name="firstName"
                    value={formData.firstName}
                    onChange={handleInputChange}
                    className={`w-full px-4 py-3 bg-white/10 border rounded-xl text-white placeholder-white/60 backdrop-blur-sm transition-all duration-300 focus:outline-none focus:ring-2 focus:scale-105 ${
                      errors.firstName 
                        ? 'border-red-400 focus:ring-red-400/50' 
                        : 'border-white/30 focus:border-white/50 focus:ring-purple-500/50'
                    }`}
                    placeholder="Tu nombre"
                  />
                  {errors.firstName && (
                    <p className="text-red-300 text-xs mt-1">{errors.firstName}</p>
                  )}
                </div>

                {/* Apellido */}
                <div>
                  <label className="block text-sm font-medium text-blue-100 mb-2">
                    Apellido *
                  </label>
                  <input
                    type="text"
                    name="lastName"
                    value={formData.lastName}
                    onChange={handleInputChange}
                    className={`w-full px-4 py-3 bg-white/10 border rounded-xl text-white placeholder-white/60 backdrop-blur-sm transition-all duration-300 focus:outline-none focus:ring-2 focus:scale-105 ${
                      errors.lastName 
                        ? 'border-red-400 focus:ring-red-400/50' 
                        : 'border-white/30 focus:border-white/50 focus:ring-purple-500/50'
                    }`}
                    placeholder="Tu apellido"
                  />
                  {errors.lastName && (
                    <p className="text-red-300 text-xs mt-1">{errors.lastName}</p>
                  )}
                </div>
              </div>
            </div>

            {/* Configuración de Pepper */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-blue-100 border-b border-white/20 pb-2">
                🤖 Configuración de Pepper
              </h3>
              
              {/* IP de Pepper */}
              <div>
                <label className="block text-sm font-medium text-blue-100 mb-2">
                  Dirección IP de Pepper *
                </label>
                <input
                  type="text"
                  name="pepperIP"
                  value={formData.pepperIP}
                  onChange={handleInputChange}
                  className={`w-full px-4 py-3 bg-white/10 border rounded-xl text-white placeholder-white/60 backdrop-blur-sm transition-all duration-300 focus:outline-none focus:ring-2 focus:scale-105 ${
                    errors.pepperIP 
                      ? 'border-red-400 focus:ring-red-400/50' 
                      : 'border-white/30 focus:border-white/50 focus:ring-purple-500/50'
                  }`}
                  placeholder="192.168.1.100"
                />
                {errors.pepperIP && (
                  <p className="text-red-300 text-xs mt-1">{errors.pepperIP}</p>
                )}
              </div>

              {/* Contraseña */}
              <div>
                <label className="block text-sm font-medium text-blue-100 mb-2">
                  Contraseña de Pepper *
                </label>
                <input
                  type="password"
                  name="pepperPassword"
                  value={formData.pepperPassword}
                  onChange={handleInputChange}
                  className={`w-full px-4 py-3 bg-white/10 border rounded-xl text-white placeholder-white/60 backdrop-blur-sm transition-all duration-300 focus:outline-none focus:ring-2 focus:scale-105 ${
                    errors.pepperPassword 
                      ? 'border-red-400 focus:ring-red-400/50' 
                      : 'border-white/30 focus:border-white/50 focus:ring-purple-500/50'
                  }`}
                  placeholder="••••••••"
                />
                {errors.pepperPassword && (
                  <p className="text-red-300 text-xs mt-1">{errors.pepperPassword}</p>
                )}
              </div>
            </div>

            {/* Botón de conexión */}
            <button
              onClick={() => navigate("/videocall")}
              disabled={isLoading}
              className="group relative w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-semibold py-4 px-6 rounded-xl transition-all duration-300 transform hover:scale-105 focus:outline-none focus:ring-4 focus:ring-purple-500/50 shadow-lg hover:shadow-purple-500/30 overflow-hidden disabled:opacity-70 disabled:cursor-not-allowed disabled:transform-none"
            >
              {/* Efecto de brillo */}
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent transform -skew-x-12 -translate-x-full group-hover:translate-x-full transition-transform duration-1000"></div>
              
              <span className="relative z-10 flex items-center justify-center gap-2">
                {isLoading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    Conectando...
                  </>
                ) : (
                  <>
                    Iniciar Conexión
                    <svg className="w-5 h-5 group-hover:translate-x-1 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  </>
                )}
              </span>
            </button>

            {/* Información adicional */}
            <div className="text-center text-xs text-white/60 mt-4">
              <p>🔒 Toda la información se mantiene segura y encriptada</p>
            </div>
          </div>
        </div>

        {/* Información de ayuda */}
        <div className="mt-6 text-center text-white/60 text-sm">
          <p>💡 Tip: Asegúrate de que Pepper esté encendido y conectado a la red</p>
        </div>
      </div>

      {/* CSS personalizado para animaciones */}
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
        
        /* Animaciones para inputs */
        input:focus {
          animation: inputFocus 0.3s ease-out;
        }
        
        @keyframes inputFocus {
          0% {
            transform: scale(1);
          }
          50% {
            transform: scale(1.02);
          }
          100% {
            transform: scale(1.05);
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