# --- Preparación para que los brazos obedezcan ---
try:
    motion_service.setBreathEnabled("Arms", 0)
except:
    pass

try:
    motion_service.setExternalCollisionProtectionEnabled("Arms", 0)
except:
    pass

try:
    motion_service.setStiffnesses(["LArm","RArm"], 0.9)
except:
    pass

# --- (3) Énfasis con brazo derecho ---
names = ["RShoulderPitch","RShoulderRoll","RElbowYaw","RElbowRoll","RWristYaw","RHand"]
angles = [
    [ 0.8,  0.15,  0.15,  0.8],
    [-0.1, -0.30, -0.30, -0.1],
    [ 0.0,  0.45,  0.45,  0.0],
    [ 0.5,  1.10,  1.10,  0.5],
    [ 0.0,  0.35, -0.25,  0.0],
    [ 0.35, 0.70,  0.70,  0.40],
]
times = [
    [0.20, 0.75, 1.35, 1.95],
    [0.20, 0.75, 1.35, 1.95],
    [0.20, 0.75, 1.35, 1.95],
    [0.20, 0.75, 1.35, 1.95],
    [0.20, 0.60, 1.00, 1.70],
    [0.20, 0.60, 1.10, 1.95],
]
motion_service.angleInterpolation(names, angles, times, 1)

# --- (5) Énfasis con brazo izquierdo ---
namesL = ["LShoulderPitch","LShoulderRoll","LElbowYaw","LElbowRoll","LWristYaw","LHand"]
anglesL = [
    [ 0.8,  0.15,  0.15,  0.8],
    [ 0.1,  0.30,  0.30,  0.1],
    [ 0.0, -0.45, -0.45,  0.0],
    [-0.5, -1.10, -1.10, -0.5],
    [ 0.0, -0.35,  0.25,  0.0],
    [ 0.35, 0.70,  0.70,  0.40],
]
timesL = [
    [0.20, 0.75, 1.35, 1.95],
    [0.20, 0.75, 1.35, 1.95],
    [0.20, 0.75, 1.35, 1.95],
    [0.20, 0.75, 1.35, 1.95],
    [0.20, 0.60, 1.00, 1.70],
    [0.20, 0.60, 1.10, 1.95],
]
motion_service.angleInterpolation(namesL, anglesL, timesL, 1)

# --- (6) Postura final de escucha ---
motion_service.angleInterpolation(
    ["HeadPitch","HeadYaw","LHand","RHand"],
    [[-0.05, -0.08], [0.0, 0.05], [0.35, 0.30], [0.35, 0.30]],
    [[ 0.20,  0.60], [0.20, 0.60], [0.20,  0.50], [0.20,  0.50]],
    1
)

# --- Re-activar protecciones y breathing ---
try:
    motion_service.setExternalCollisionProtectionEnabled("Arms", 1)
except:
    pass
try:
    motion_service.setBreathEnabled("Arms", 1)
except:
    pass
