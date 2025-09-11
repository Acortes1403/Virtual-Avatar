# (Opcional) asegurar control del torso
try:
    motion_service.setBreathEnabled("Body", 0)
except:
    pass
try:
    motion_service.setStiffnesses(["Torso"], 0.9)
except:
    pass

# --- Torso: adelante ←→ atrás (HipPitch) ---
motion_service.angleInterpolation(
    ["HipPitch"],
    [[ 0.00, -0.08,  0.08,  0.00 ]],     # radianes (suave y seguro)
    [[ 0.30,  0.90,  1.50,  2.00 ]],     # tiempos (s) crecientes > 0
    1
)

# --- Torso: izquierda ←→ derecha (HipRoll) ---
motion_service.angleInterpolation(
    ["HipRoll"],
    [[ 0.00,  0.12, -0.12,  0.00 ]],
    [[ 0.30,  0.90,  1.50,  2.00 ]],
    1
)

# (Opcional) volver a activar respiración suave
try:
    motion_service.setBreathEnabled("Body", 1)
except:
    pass
