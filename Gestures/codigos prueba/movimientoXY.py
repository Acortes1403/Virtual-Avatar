motion_service.setMoveArmsEnabled(0, 0)  # sin balanceo de brazos

# --- Configuración lenta/segura (ajusta al gusto) ---
cfg = [
    ["MaxVelXY",     0.10],  # 10% de velocidad lineal
    ["MaxVelTheta",  0.10],  # 10% de velocidad angular
    ["MaxAccXY",     0.20],
    ["MaxAccTheta",  0.20],
]

# Distancias (metros)
d_fwd  = 0.30   # 30 cm hacia adelante/atrás
d_side = 0.25   # 25 cm hacia la izquierda/derecha

# ================== OPCIÓN 1: moveTo (recomendada) ==================
try:
    # Adelante recto
    motion_service.moveTo( d_fwd, 0.0, 0.0, cfg)
    time.sleep(0.4)
    # Atrás recto (regresa al punto)
    motion_service.moveTo(-d_fwd, 0.0, 0.0, cfg)
    time.sleep(0.6)

    # Izquierda recto (lateral puro: x=0, theta=0, y>0)
    motion_service.moveTo(0.0,  d_side, 0.0, cfg)
    time.sleep(0.4)
    # Derecha recto (regresa al punto: y<0)
    motion_service.moveTo(0.0, -d_side, 0.0, cfg)

except:
    # ================== OPCIÓN 2: moveToward (fallback por tiempo) ==================
    vx = 0.08  # m/s hacia adelante/atrás
    vy = 0.08  # m/s lateral
    # tiempos necesarios para recorrer la distancia deseada
    t_fwd  = d_fwd  / abs(vx) if vx != 0 else 0
    t_side = d_side / abs(vy) if vy != 0 else 0
    theta = 0.785 # 45° en radianes (para giros)

    # Adelante
    motion_service.moveToward( vx, 0.0, 0.0)
    time.sleep(t_fwd)
    motion_service.stopMove()
    time.sleep(0.4)

    # Atrás (regresa)
    motion_service.moveToward(-vx, 0.0, 0.0)
    time.sleep(t_fwd)
    motion_service.stopMove()
    time.sleep(0.6)

    # Izquierda (lateral puro)
    motion_service.moveToward(0.0, vy, 0.0)
    time.sleep(t_side)
    motion_service.stopMove()
    time.sleep(0.4)

    # Derecha (regresa)
    motion_service.moveToward(0.0, -vy, 0.0)
    time.sleep(t_side)
    motion_service.stopMove()