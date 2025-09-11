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

def anim_confusion_v1(speed_main=0.14, speed_pulse=0.20, arm_pitch=-0.02):
    # 0) Base: mano dcha al mentón, brazo izq relajado
    _do_with_speed(
        ["LHand","RHand",
         "LShoulderPitch","RShoulderPitch","LShoulderRoll","RShoulderRoll",
         "LElbowRoll","RElbowRoll","LElbowYaw","RElbowYaw",
         "LWristYaw","RWristYaw",
         "HipPitch","HeadPitch","HeadYaw"],
        [ 0.35,   0.25,
          arm_pitch, -0.10,   0.10,  -0.08,
         -1.5,      1.5,   -0.25,   0.90,
         -0.08,       0.25,
          0.00,      -0.04,   0.00],
        speed_main
    )

    # 1) "¿Hmm?" — leve inclinación a la izq y hombros un poco arriba
    _do_with_speed(
        ["HeadYaw","HipRoll","LShoulderRoll","RShoulderRoll","HeadPitch"],
        [ 0.18,     0.05,     0.22,           -0.22,         -0.06],
        speed_pulse
    )
    # 2) Al otro lado (oscilación corta)
    _do_with_speed(
        ["HeadYaw","HipRoll","LShoulderRoll","RShoulderRoll","HeadPitch"],
        [-0.18,    -0.05,     0.12,           -0.12,         -0.05],
        speed_pulse
    )

    # ===== 3) Subgesto de “pensar” — MÁS cierre de codos (ElbowYaw en ambos brazos) =====

    # Acercar mentón con la derecha y mantener ambos ElbowYaw cerrados
    _do_with_speed(
        ["RElbowYaw","RElbowRoll","RWristYaw","RHand","HeadPitch","LElbowYaw"],
        [ 1.15,        1.15,       0.30,      0.22,   -0.07,     -0.55],
        speed_pulse
    )
    # Pequeño “release” manteniendo cierre (ligeramente menos extremo)
    _do_with_speed(
        ["RElbowYaw","RElbowRoll","RWristYaw","RHand","HeadPitch","LElbowYaw"],
        [ 1.05,        1.05,       0.25,      0.25,   -0.05,     -0.45],
        speed_pulse
    )

    # 4) Encogida suave de hombros y recentrado
    _do_with_speed(
        ["LShoulderRoll","RShoulderRoll","HeadYaw","HipRoll"],
        [ 0.16,          -0.16,          0.00,     0.00],
        speed_main
    )

    # 5) Volver a NEUTRAL a la MISMA velocidad base
    neutral_user_match_speed(speed_main)



prep()
anim_confusion_v1()   # ajusta speed_main/speed_pulse/arm_pitch
restore()