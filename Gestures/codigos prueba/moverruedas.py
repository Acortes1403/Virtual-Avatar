motion_service.setMoveArmsEnabled(0, 0)

# 3) Reducir velocidades para hacerlo lento/seguro
cfg = [
    ["MaxVelXY",     1],   # 5% vel lineal (aunque giraremos en el lugar)
    ["MaxVelTheta",  1],   # 10% vel angular
    ["MaxAccXY",     1],   # aceleración moderada
    ["MaxAccTheta",  1]
]

# 4) Girar +45° en el lugar (theta = +pi/4 ≈ 0.785)
motion_service.moveTo(0.0, 0.0, 0.785, cfg)

# Pausa corta
time.sleep(0.8)

# 5) Girar -45° para volver a la orientación original
motion_service.moveTo(0.0, 0.0, -0.785, cfg)

# Pausa corta
time.sleep(0.8)

# 4) Girar +45° en el lugar (theta = +pi/4 ≈ 0.785)
motion_service.moveTo(0.0, 0.0, -0.785, cfg)

# Pausa corta
time.sleep(0.8)

# 5) Girar -45° para volver a la orientación original
motion_service.moveTo(0.0, 0.0, 0.785, cfg)