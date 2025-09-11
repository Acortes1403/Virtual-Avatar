# ---------- helpers ----------
def _do_with_speed(names, targets, speed):
    motion_service.angleInterpolationWithSpeed(names, targets, speed)

def prep():
    try: motion_service.wakeUp()
    except: pass
    try: motion_service.setBreathEnabled("Body", 0)
    except: pass
    try: motion_service.setExternalCollisionProtectionEnabled("Arms", 0)
    except: pass
    try: motion_service.setStiffnesses(["Head","LArm","RArm","Torso"], 0.9)
    except: pass

def neutral_user_match_speed(speed_fraction):
    _do_with_speed(
        ["HeadPitch","HeadYaw","LHand","RHand",
         "LShoulderPitch","RShoulderPitch","LElbowRoll","RElbowRoll",
         "HipPitch","HipRoll"],
        [-0.08, 0.05, 0.30, 0.30,
          1, 1, -0.30, 0.30, 0.00, 0.00],
        speed_fraction
    )

def restore():
    try: motion_service.setExternalCollisionProtectionEnabled("Arms", 1)
    except: pass
    try: motion_service.setBreathEnabled("Body", 1)
    except: pass
    # try: motion_service.rest()
    # except: pass

def anim_love_affection_v2(speed_main=0.68, speed_squeeze=0.85, arm_pitch=0.40):
    """
    Love/Affection:
      - Brazos en 'L' cerca del pecho (sin subir todo el brazo).
      - Dos apretones suaves de abrazo.
      - Termina en neutral a la MISMA velocidad base.
    Parámetros:
      speed_main: velocidad base (fluida).
      speed_squeeze: acento de los “apretones”.
      arm_pitch: elevación de hombro (ShoulderPitch) moderada (≈ mitad).
    """

    # 0) Colocar brazos en 'L' frente al pecho (manos semiabiertas), torso neutro
    _do_with_speed(
        ["LHand","RHand",
         "LShoulderPitch","RShoulderPitch","LShoulderRoll","RShoulderRoll",
         "LElbowRoll","RElbowRoll","LElbowYaw","RElbowYaw",
         "LWristYaw","RWristYaw","HipPitch","HipRoll"],
        [ 0.35, 0.35,
          arm_pitch, arm_pitch,  0.16,  -0.16,
         -1.05,     1.05,       -0.40,   0.40,
         -0.15,     0.15,        0.00,   0.00],
        speed_main
    )

    # 1) Cerrar abrazo (cruzar un poco los antebrazos hacia el centro)
    _do_with_speed(
        ["LElbowYaw","RElbowYaw","LElbowRoll","RElbowRoll","LWristYaw","RWristYaw","HipPitch"],
        [-0.85,       0.85,       -1.12,       1.12,       -0.25,      0.25,      -0.02],
        speed_main
    )

    # 2) Apretón 1 (acento suave) + manos un poco más cerradas
    _do_with_speed(
        ["LElbowRoll","RElbowRoll","LHand","RHand","HipPitch"],
        [-1.18,        1.18,       0.28,  0.28,  -0.03],
        speed_squeeze
    )
    # Soltar parcial
    _do_with_speed(
        ["LElbowRoll","RElbowRoll","LHand","RHand","HipPitch"],
        [-1.02,        1.02,       0.35,  0.35,   0.00],
        speed_squeeze
    )

    # 3) Apretón 2 (repite con leve inclinación)
    _do_with_speed(["HipPitch"], [-0.02], speed_main)
    _do_with_speed(
        ["LElbowRoll","RElbowRoll","LHand","RHand"],
        [-1.18,        1.18,       0.28,  0.28],
        speed_squeeze
    )
    _do_with_speed(
        ["LElbowRoll","RElbowRoll","LHand","RHand","HipPitch"],
        [-1.02,        1.02,       0.35,  0.35,   0.00],
        speed_squeeze
    )

    # 4) Abrir un poquito (deshacer cruce) manteniendo la 'L'
    _do_with_speed(
        ["LElbowYaw","RElbowYaw","LElbowRoll","RElbowRoll","LShoulderPitch","RShoulderPitch"],
        [-0.50,       0.50,       -1.05,        1.05,        arm_pitch,       arm_pitch],
        speed_main
    )

    # 5) Regresar a NEUTRAL a la MISMA velocidad base
    neutral_user_match_speed(speed_main)

prep()
anim_love_affection_v2()   # ajusta speed_main/speed_squeeze si
restore()
