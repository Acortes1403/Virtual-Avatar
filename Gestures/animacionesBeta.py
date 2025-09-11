# ================== Utilidades y postura base ==================
# motion_service.rest()
# motion_service.wakeUp()

def _do(names, angles, times):
    motion_service.angleInterpolation(names, angles, times, 1)  # isAbsolute=1

def neutral_zero():
    # Tu "0": brazos al frente, manos semiabiertas, cabeza centrada, torso neutro
    names  = ["LShoulderPitch","RShoulderPitch","LShoulderRoll","RShoulderRoll",
              "LElbowYaw","RElbowYaw","LElbowRoll","RElbowRoll",
              "LWristYaw","RWristYaw","LHand","RHand",
              "HeadYaw","HeadPitch","HipPitch","HipRoll"]
    target = [0.0, 0.0, 0.05,-0.05, 0.0, 0.0, -0.3, 0.3, 0.0, 0.0, 0.40,0.40, 0.0,-0.02, 0.0, 0.0]
    _do(names, [[a] for a in target], [[0.50] for _ in names])

# Opcional: garantizar control suave (no falla si no existe)
try: motion_service.setBreathEnabled("Body", 0)
except: pass
try: motion_service.setStiffnesses(["Head","LArm","RArm","Torso"], 0.9)
except: pass

# ================== 1) EUPHORIA ==================
def anim_euphoria():
    neutral_zero()
    # V alta, saltitos de codo, leve inclinación adelante
    names = ["LShoulderPitch","RShoulderPitch","LShoulderRoll","RShoulderRoll",
             "LElbowRoll","RElbowRoll","LWristYaw","RWristYaw",
             "HeadYaw","HeadPitch","HipPitch"]
    angles = [
        [ 0.0, -0.35, -0.20],   # LShPitch sube
        [ 0.0, -0.35, -0.20],   # RShPitch sube
        [ 0.05, 0.55, 0.50],    # LShRoll abre
        [-0.05,-0.55,-0.50],    # RShRoll abre
        [-0.5, -0.9, -0.7],     # LElbowRoll beats
        [ 0.5,  0.9,  0.7],     # RElbowRoll
        [-0.2, -0.5, -0.2],     # LWristYaw beat
        [ 0.2,  0.5,  0.2],     # RWristYaw
        [ 0.00, 0.18, 0.00],    # HeadYaw ritmo
        [-0.02,-0.06,-0.04],    # HeadPitch
        [ 0.00,-0.05, 0.00],    # HipPitch mini bounce
    ]
    times = [[0.30, 0.85, 1.30] for _ in names]
    _do(names, angles, times)
    neutral_zero()

# ================== 2) JOY ==================
def anim_joy():
    neutral_zero()
    # Sway de cuerpo + manos abren/cierre leve
    _do(["HipRoll","HeadYaw"], [[0.00, 0.12,-0.12, 0.00],[0.00, 0.10,-0.10, 0.00]],
        [[0.30,0.90,1.50,2.00],[0.30,0.90,1.50,2.00]])
    _do(["LHand","RHand"], [[0.40,0.65,0.45],[0.40,0.65,0.45]],
        [[0.30,1.10,1.80],[0.30,1.10,1.80]])
    neutral_zero()

# ================== 3) SERENITY ==================
def anim_serenity():
    neutral_zero()
    names = ["HeadPitch","HipPitch","LShoulderRoll","RShoulderRoll","LHand","RHand"]
    angles = [[-0.02,-0.08,-0.04],[0.00,-0.04,0.00],[0.05,0.12,0.08],[-0.05,-0.12,-0.08],[0.40,0.35,0.40],[0.40,0.35,0.40]]
    times  = [[0.30,0.90,1.60] for _ in names]
    _do(names, angles, times)

# ================== 4) CALMNESS ==================
def anim_calmness():
    neutral_zero()
    # Respiración simulada: torso + cabeza acompaña
    _do(["HipPitch"], [[0.00,-0.06, 0.06, 0.00]], [[0.30,0.90,1.50,2.10]])
    _do(["HeadPitch"], [[-0.02,-0.05,-0.01,-0.02]], [[0.30,0.90,1.50,2.10]])

# ================== 5) SATISFACTION ==================
def anim_satisfaction():
    neutral_zero()
    nod = [[-0.02,-0.18, 0.10,-0.02]]
    tim = [[ 0.20, 0.80, 1.40, 1.90]]
    _do(["HeadPitch"], nod, tim)
    # pequeño lift de hombros
    _do(["LShoulderRoll","RShoulderRoll"], [[0.05,0.18,0.08],[-0.05,-0.18,-0.08]],
        [[0.20,0.80,1.40],[0.20,0.80,1.40]])

# ================== 6) LOVE / AFFECTION ==================
def anim_love_affection():
    neutral_zero()
    names = ["LShoulderPitch","RShoulderPitch","LElbowYaw","RElbowYaw",
             "LElbowRoll","RElbowRoll","HeadPitch","HipPitch"]
    angles = [
        [ 0.0, 0.10, 0.00],  # brazos se acercan al pecho desde frente
        [ 0.0, 0.10, 0.00],
        [-0.6,-0.9,-0.5],   # cruzan
        [ 0.6, 0.9, 0.5],
        [-0.6,-0.9,-0.7],
        [ 0.6, 0.9, 0.7],
        [-0.02,-0.08,-0.04],# cabeza baja suave
        [ 0.00,-0.03, 0.00],# leve inclinación
    ]
    times = [[0.35,0.95,1.50] for _ in names]
    _do(names, angles, times)
    neutral_zero()

# ================== 7) SURPRISE ==================
def anim_surprise():
    neutral_zero()
    _do(["HeadPitch"], [[-0.02,-0.20,-0.06]], [[0.20,0.70,1.10]])  # “¡oh!”
    names = ["LShoulderRoll","RShoulderRoll","LHand","RHand","HipPitch"]
    angles = [[0.05,0.40,0.25],[-0.05,-0.40,-0.25],[0.40,1.00,0.70],[0.40,1.00,0.70],[0.00,-0.04,0.00]]
    times  = [[0.20,0.70,1.10] for _ in names]
    _do(names, angles, times)
    neutral_zero()

# ================== 8) FEAR ==================
def anim_fear():
    neutral_zero()
    # Retrae brazos cerca del torso, inclina atrás y mira a lados
    names = ["LShoulderPitch","RShoulderPitch","LElbowRoll","RElbowRoll","HeadYaw","HipPitch"]
    angles = [[ 0.0, 0.25, 0.15],[ 0.0, 0.25, 0.15],[-0.3,-0.1,-0.2],[0.3,0.1,0.2],[0.00,0.20,-0.20,0.00],[0.00, 0.05, 0.00]]
    times  = [[0.25,0.80,1.30],[0.25,0.80,1.30],[0.25,0.80,1.30],[0.25,0.80,1.30],[0.25,0.70,1.20,1.60],[0.25,0.80,1.30]]
    _do(names, angles, times)
    neutral_zero()

# ================== 9) ANXIETY ==================
def anim_anxiety():
    neutral_zero()
    # Micro-movimientos rápidos y repetidos (sin range)
    names = ["LElbowRoll","RElbowRoll","LWristYaw","RWristYaw","HeadYaw","HipRoll"]
    angles = [
        [-0.4,-0.5,-0.3,-0.45], [0.4,0.5,0.3,0.45],
        [-0.2,-0.4,-0.1,-0.3],  [0.2,0.4,0.1,0.3],
        [ 0.04,-0.04,0.06,-0.02],[0.00,0.04,-0.04,0.00]
    ]
    times  = [
        [0.20,0.45,0.70,0.95],[0.20,0.45,0.70,0.95],
        [0.20,0.45,0.70,0.95],[0.20,0.45,0.70,0.95],
        [0.20,0.45,0.70,0.95],[0.20,0.45,0.70,0.95]
    ]
    _do(names, angles, times)
    neutral_zero()

# ================== 10) ANGER ==================
def anim_anger():
    neutral_zero()
    # Cruce firme + “no” claro con cabeza
    names = ["LElbowYaw","RElbowYaw","LElbowRoll","RElbowRoll","HeadYaw","HipPitch"]
    angles = [[-0.6,-1.0,-0.8],[0.6,1.0,0.8],[-0.6,-1.0,-0.9],[0.6,1.0,0.9],[0.00,0.45,-0.45,0.00],[0.00,0.02,0.00]]
    times  = [[0.25,0.65,1.10],[0.25,0.65,1.10],[0.25,0.65,1.10],[0.25,0.65,1.10],[0.25,0.65,1.05,1.45],[0.25,0.65,1.10]]
    _do(names, angles, times)
    neutral_zero()

# ================== 11) FRUSTRATION ==================
def anim_frustration():
    neutral_zero()
    # Brazos bajan un poco y “sacuden” afuera, exhalo con torso
    names = ["LShoulderPitch","RShoulderPitch","LShoulderRoll","RShoulderRoll","LElbowRoll","RElbowRoll","HipPitch","HeadPitch"]
    angles = [[0.0,0.15,0.05],[0.0,0.15,0.05],[0.05,0.30,0.20],[-0.05,-0.30,-0.20],[-0.3,-0.6,-0.4],[0.3,0.6,0.4],[0.00,0.03,0.00],[-0.02,0.02,-0.03]]
    times  = [[0.25,0.75,1.25] for _ in names]
    _do(names, angles, times)
    neutral_zero()

# ================== 12) SADNESS ==================
def anim_sadness():
    neutral_zero()
    names = ["HeadPitch","HeadYaw","LShoulderPitch","RShoulderPitch","LHand","RHand","HipPitch"]
    angles = [[-0.02,-0.14,-0.18],[0.0,-0.06,0.0],[0.0,0.10,0.15],[0.0,0.10,0.15],[0.40,0.30,0.25],[0.40,0.30,0.25],[0.00,0.02,0.00]]
    times  = [[0.30,0.90,1.50] for _ in names]
    _do(names, angles, times)

# ================== 13) BOREDOM ==================
def anim_boredom():
    neutral_zero()
    _do(["HeadYaw"], [[0.00, 0.35, 0.35]], [[0.40, 1.00, 1.60]])  # mira a un lado y se queda
    names = ["LShoulderPitch","RShoulderPitch","LElbowYaw","RElbowYaw","LHand","RHand"]
    angles = [[0.0,0.05,0.0],[0.0,0.05,0.0],[-0.4,-0.7,-0.5],[0.4,0.7,0.5],[0.40,0.35,0.40],[0.40,0.35,0.40]]
    times  = [[0.50,1.20,1.80] for _ in names]
    _do(names, angles, times)
    neutral_zero()

# ================== 14) GUILT ==================
def anim_guilt():
    neutral_zero()
    # Manos cerca del pecho + cabeza abajo y ligera torsión de torso
    names = ["LElbowYaw","RElbowYaw","LElbowRoll","RElbowRoll","LShoulderPitch","RShoulderPitch","HeadPitch","HipRoll"]
    angles = [[-0.8,-0.9,-0.7],[0.8,0.9,0.7],[-0.7,-0.9,-0.8],[0.7,0.9,0.8],[0.0,0.08,0.02],[0.0,0.08,0.02],[-0.02,-0.12,-0.10],[0.00,0.05,0.00]]
    times  = [[0.40,1.00,1.50] for _ in names]
    _do(names, angles, times)
    neutral_zero()

# ================== 15) NOSTALGIA ==================
def anim_nostalgia():
    neutral_zero()
    # Mirada arriba-derecha, manos flotan, leve arqueo torso
    names = ["HeadYaw","HeadPitch","LHand","RHand","HipPitch","LShoulderPitch","RShoulderPitch"]
    angles = [[0.00, 0.18, 0.15],[ -0.02, -0.01, 0.03],[0.40,0.55,0.45],[0.40,0.55,0.45],[0.00,-0.03,0.00],[0.0,-0.05,0.0],[0.0,-0.05,0.0]]
    times  = [[0.30,0.95,1.60] for _ in names]
    _do(names, angles, times)
    neutral_zero()

# ================== Ejemplos de uso ==================
# neutral_zero()
# anim_euphoria()
# anim_joy()
# anim_serenity()
# anim_calmness()
# anim_satisfaction()
# anim_love_affection()
# anim_surprise()
# anim_fear()
# anim_anxiety()
# anim_anger()
# anim_frustration()
# anim_sadness()
# anim_boredom()
# anim_guilt()
# anim_nostalgia()