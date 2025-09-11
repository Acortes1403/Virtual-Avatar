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

# ---------- animación ----------
def anim_joy_v3(speed_main=0.72, speed_pulse=0.92, arm_pitch=0.5):
    # arm_pitch controla la elevación de hombros.
    # Si antes usabas -0.15, aquí va ~la mitad (-0.08). Ajusta a gusto.

    # 0) Puños cerrados + “L” (codo ~90°) + hombros con arm_pitch (mitad de elevación)
    _do_with_speed(
        ["LHand","RHand",
         "LShoulderPitch","RShoulderPitch","LShoulderRoll","RShoulderRoll",
         "LElbowRoll","RElbowRoll","LElbowYaw","RElbowYaw"],
        [ 0.0,   0.0,
          arm_pitch, arm_pitch,  0.10,  -0.10,
         -1.05,    1.05,        -0.20,   0.20],
        speed_main
    )

    # ===== Ciclo 1 =====
    # Sway MUY suave con torso/cabeza (puños siguen cerrados, brazos en L)
    _do_with_speed(["HipRoll","HeadYaw"], [ 0.05,  0.08], speed_main)   # izquierda
    _do_with_speed(["HipRoll","HeadYaw"], [-0.05, -0.08], speed_main)   # derecha

    # Acento de antebrazos (manteniendo la “L”) + asentimiento suave
    _do_with_speed(
        ["LElbowRoll","RElbowRoll","HeadPitch","HipPitch"],
        [-1.12,        1.12,        -0.07,      -0.01],
        speed_pulse
    )
    _do_with_speed(
        ["LElbowRoll","RElbowRoll","HeadPitch","HipPitch"],
        [-0.98,        0.98,        -0.03,       0.00],
        speed_pulse
    )

    # ===== Ciclo 2 =====
    _do_with_speed(["HipRoll","HeadYaw"], [ 0.05,  0.08], speed_main)
    _do_with_speed(["HipRoll","HeadYaw"], [-0.05, -0.08], speed_main)
    _do_with_speed(["HeadYaw"], [0.10], speed_main)  # giro alegre corto

    _do_with_speed(
        ["LElbowRoll","RElbowRoll","HeadPitch","HipPitch"],
        [-1.12,        1.12,        -0.07,      -0.01],
        speed_pulse
    )
    _do_with_speed(
        ["LElbowRoll","RElbowRoll","HeadPitch","HeadYaw","HipPitch"],
        [-0.98,        0.98,        -0.03,       0.00,     0.00],
        speed_pulse
    )
    # Volver a NEUTRAL a la MISMA velocidad base
    neutral_user_match_speed(speed_main)

# ---------- ejecución ----------
prep()
anim_joy_v3()   # ajusta speed_main/speed_pulse si quieres más “punch”
restore()