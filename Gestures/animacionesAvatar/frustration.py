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

def anim_anger_v2(speed_main=0.75, speed_snap=0.96, arm_pitch=-0.12):
    # 0) POSE inicial (como la foto): brazos arriba junto a la cabeza, manos abiertas
    _do_with_speed(
        ["LHand","RHand",
         "LShoulderPitch","RShoulderPitch","LShoulderRoll","RShoulderRoll",
         "LElbowRoll","RElbowRoll","LElbowYaw","RElbowYaw",
         "LWristYaw","RWristYaw","HipPitch","HeadPitch","HeadYaw"],
        [ 1.00, 1.00,
          arm_pitch, arm_pitch,   0.48,  -0.48,
         -1.05,     1.05,        -0.40,   0.40,
         -0.80,      0.80,       -0.02,   -0.04,    0.00],
        speed_main
    )

    # Pausa breve para "marcar" la pose
    try:
        import time; time.sleep(0.25)
    except:
        pass

    # 1) Molestia: cerrar puños + primer "no" con la cabeza
    _do_with_speed(["LHand","RHand","HeadYaw"], [0.0, 0.0,  0.24], speed_snap)

    # 2) Bajar AMBOS brazos (mitad de recorrido) con orientación de codo y muñeca
    _do_with_speed(
        ["LShoulderPitch","RShoulderPitch",
         "LShoulderRoll","RShoulderRoll",
         "LElbowRoll","RElbowRoll","LElbowYaw","RElbowYaw",
         "LWristYaw","RWristYaw","HipRoll"],
        [ 0.20,            0.20,
          0.10,           -0.10,
         -0.85,            0.85,  -0.70,   0.70,
         -0.35,            0.35,  -0.03],
        speed_main
    )

    # 3) Segundo "no" y bajar un poco más ambos brazos
    _do_with_speed(["HeadYaw"], [-0.24], speed_snap)
    _do_with_speed(
        ["LShoulderPitch","RShoulderPitch",
         "LElbowRoll","RElbowRoll",
         "LWristYaw","RWristYaw","HipRoll"],
        [ 0.35,            0.35,
         -0.60,            0.60,
         -0.20,            0.20,   0.00],
        speed_main
    )
    _do_with_speed(["HeadYaw"], [0.00], speed_snap)

    # 4) Regreso a NEUTRAL a la MISMA velocidad base
    neutral_user_match_speed(speed_main)



prep()
anim_anger_v2()   # ajusta speed_main/speed_snap/arm_pitch si
restore()