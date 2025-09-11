# ====== Calma (termina en neutral) — listo para pegar ======
# Requiere: motion_service ya disponible en tu entorno

# ---------- helpers ----------
def _do_with_speed(names, targets, speed):
    motion_service.angleInterpolationWithSpeed(names, targets, speed)

# ---------- preparación / neutral / restore ----------
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
          1, 1, -0.30, 0.30,
          0.00, 0.00],
        speed_fraction
    )

def restore():
    try: motion_service.setExternalCollisionProtectionEnabled("Arms", 1)
    except: pass
    try: motion_service.setBreathEnabled("Body", 1)
    except: pass

def anim_deep_breath_v1(speed_main=0.55, arm_pitch=1):
    # Postura base: brazos en “L”, hombros apenas elevados, manos semis
    _do_with_speed(
        ["LHand","RHand",
         "LShoulderPitch","RShoulderPitch",
         "LWristYaw","RWristYaw","HipPitch","HipRoll"],
        [ 0.35, 0.35,
          arm_pitch, arm_pitch,  
          0.20, -0.10,     0.10,        0.00,   0.00],
        speed_main
    )

    # ===== Ciclo 1 — INHALA (abre) =====
    _do_with_speed(
        ["HipPitch","LShoulderRoll","RShoulderRoll","LHand","RHand","LWristYaw","RWristYaw"],
        [-0.06,     0.16,          -0.16,          0.65,   0.65,   -0.18,      0.18],
        speed_main
    )
    # EXHALA (cierra) — un poco más larga en pasos (pero misma speed)
    _do_with_speed(
        ["HipPitch","LShoulderRoll","RShoulderRoll","LHand","RHand"],
        [-0.03,     0.13,          -0.13,          0.48,   0.48],
        speed_main
    )
    _do_with_speed(
        ["HipPitch","LShoulderRoll","RShoulderRoll","LHand","RHand"],
        [ 0.00,     0.10,          -0.10,          0.35,   0.35],
        speed_main
    )

    # ===== Ciclo 2 — INHALA =====
    _do_with_speed(
        ["HipPitch","LShoulderRoll","RShoulderRoll","LHand","RHand","LWristYaw","RWristYaw"],
        [-0.06,     0.16,          -0.16,          0.65,   0.65,   -0.18,      0.18],
        speed_main
    )
    # EXHALA (en dos pasitos para que se sienta profunda)
    _do_with_speed(
        ["HipPitch","LShoulderRoll","RShoulderRoll","LHand","RHand"],
        [-0.03,     0.13,          -0.13,          0.48,   0.48],
        speed_main
    )
    _do_with_speed(
        ["HipPitch","LShoulderRoll","RShoulderRoll","LHand","RHand"],
        [ 0.00,     0.10,          -0.10,          0.35,   0.35],
        speed_main
    )
    # Vuelve a NEUTRAL a la MISMA velocidad base
    neutral_user_match_speed(speed_main)

prep()
anim_deep_breath_v1()
restore()