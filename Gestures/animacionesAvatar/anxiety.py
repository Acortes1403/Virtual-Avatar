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

def anim_anxiety_v2(speed_main=0.70, speed_jitter=0.93, arm_pitch=1.00):
    # Postura base: L marcada, puños cerrados, hombros casi quietos
    _do_with_speed(
        ["LHand","RHand",
         "LShoulderPitch","RShoulderPitch","LShoulderRoll","RShoulderRoll",
         "LElbowRoll","RElbowRoll","LElbowYaw","RElbowYaw",
         "LWristYaw","RWristYaw","HipPitch","HipRoll","HeadYaw","HeadPitch"],
        [ 0.0, 0.0,
          arm_pitch, arm_pitch,  0.08,  -0.08,
         -1.05,     1.05,       -0.45,   0.45,
         -0.10,     0.10,        0.00,    0.00,   0.00,    -0.04],
        speed_main
    )

    # Jitter 1: aprieta codos, gira muñecas, mirada corta a la izq, sway mínimo
    _do_with_speed(
        ["LElbowRoll","RElbowRoll","LWristYaw","RWristYaw","HeadYaw","HipRoll","HipPitch"],
        [-1.14,        1.14,        -0.30,      0.30,      0.06,     0.03,     -0.01],
        speed_jitter
    )
    _do_with_speed(
        ["LElbowRoll","RElbowRoll","LWristYaw","RWristYaw","HeadYaw","HipRoll","HipPitch"],
        [-0.96,        0.96,        -0.08,      0.08,     -0.06,    -0.03,      0.00],
        speed_jitter
    )

    # Jitter 2: espejo al otro lado
    _do_with_speed(
        ["LElbowRoll","RElbowRoll","LWristYaw","RWristYaw","HeadYaw","HipRoll","HipPitch"],
        [-1.12,        1.12,        -0.28,      0.28,     -0.06,    -0.03,     -0.01],
        speed_jitter
    )
    _do_with_speed(
        ["LElbowRoll","RElbowRoll","LWristYaw","RWristYaw","HeadYaw","HipRoll","HipPitch"],
        [-0.98,        0.98,        -0.10,      0.10,      0.00,     0.00,      0.00],
        speed_jitter
    )

    # Reafirmar “L” tensa y puños cerrados antes de volver
    _do_with_speed(
        ["LShoulderPitch","RShoulderPitch","LElbowRoll","RElbowRoll","LHand","RHand","LWristYaw","RWristYaw"],
        [ arm_pitch,       arm_pitch,       -1.05,        1.05,       0.0,   0.0,   -0.10,       0.10],
        speed_main
    )

    # Regreso a NEUTRAL a la MISMA velocidad base
    neutral_user_match_speed(speed_main)

prep()
anim_anxiety_v2()   # ajusta speed_main/speed_jitter/arm_pitch
restore()