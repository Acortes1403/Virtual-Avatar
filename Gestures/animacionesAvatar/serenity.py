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

def anim_serenity_v2(speed_main=0.2, arm_pitch=1):
    # Postura inicial: brazos relajados (sin bajar), manos semis, cabeza NO se toca
    _do_with_speed(
        ["LHand","RHand",
         "LShoulderPitch","RShoulderPitch","LShoulderRoll","RShoulderRoll",
         "LElbowRoll","RElbowRoll","LElbowYaw","RElbowYaw","LWristYaw","RWristYaw"],
        [ 0.35, 0.35,
          arm_pitch, arm_pitch,  0.12, -0.12,
         -0.55,     0.55,       -0.20,  0.20,     -0.10,     0.10],
        speed_main
    )

    # Respiración/sway muy suave SOLO con torso
    # Ciclo 1
    _do_with_speed(["HipPitch"], [-0.03], speed_main)
    _do_with_speed(["HipPitch"], [ 0.00], speed_main)
    _do_with_speed(["HipRoll"], [ 0.04], speed_main)
    _do_with_speed(["HipRoll"], [ 0.00], speed_main)

    # Ciclo 2 (espejo)
    _do_with_speed(["HipPitch"], [-0.03], speed_main)
    _do_with_speed(["HipPitch"], [ 0.00], speed_main)
    _do_with_speed(["HipRoll"], [-0.04], speed_main)
    _do_with_speed(["HipRoll"], [ 0.00], speed_main)

    # Re-centrar hombros muy leve (sin subir brazo)
    _do_with_speed(["LShoulderRoll","RShoulderRoll"], [0.10, -0.10], speed_main)

    # Volver a NEUTRAL a la MISMA velocidad base (como la cabeza no se movió, no cambia)
    neutral_user_match_speed(speed_main)

prep()
anim_serenity_v2()
restore()
