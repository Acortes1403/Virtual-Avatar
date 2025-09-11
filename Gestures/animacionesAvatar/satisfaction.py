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

def anim_satisfaction_v2(speed_main=0.68, arm_pitch=0.5):
    # Postura base: brazo derecho listo (tu versión)
    _do_with_speed(
        ["RHand",
         "RShoulderPitch","RShoulderRoll",
         "RElbowRoll","RElbowYaw",
         "HipPitch","HipRoll"],
        [ 0.35,
          arm_pitch,  -0.12,
          1.00,        0.25,
         -0.01,        0.00],
        speed_main
    )

    # Asentimiento suave (sí) x2 — sin bajar los brazos
    _do_with_speed(["HeadPitch"], [-0.10], speed_main)  # baja
    _do_with_speed(["HeadPitch"], [-0.04], speed_main)  # sube
    _do_with_speed(["HeadPitch"], [-0.10], speed_main)  # baja
    _do_with_speed(["HeadPitch"], [-0.05], speed_main)  # sube y queda

    # ===== Pulgar hacia arriba (simulado) con brazo derecho =====
    # 1) Cierra puño
    _do_with_speed(["RHand"], [0.0], speed_main)

    # 2) Orienta el antebrazo/mano para "👍":
    #    - RElbowRoll ~1.10 (codo marcado, brazo en L)
    #    - RShoulderRoll -0.25 (ligero abducción)
    #    - RElbowYaw +0.55 (orienta el antebrazo)
    #    - RWristYaw -1.10 (gira puño para que "parezca" pulgar arriba)
    _do_with_speed(
        ["RElbowRoll","RShoulderPitch","RShoulderRoll","RElbowYaw","RWristYaw"],
        [ 1.10,        arm_pitch,      -0.25,           0.55,       1.10],
        speed_main
    )

    # (Opcional) mantén un instante la pose
    try:
        import time
        time.sleep(0.25)
    except:
        pass

    # ===== Resto del gesto "satisfecho" (tu bloque original) =====
    _do_with_speed(
        ["LElbowYaw","RElbowYaw","LElbowRoll","RElbowRoll","HipPitch"],
        [-0.35,       0.35,       -0.88,       0.88,       -0.03],
        speed_main
    )

    # Re-centrar hombros muy leve (look limpio)
    _do_with_speed(["LShoulderRoll","RShoulderRoll"], [0.10, -0.10], speed_main)

    # (Opcional) volver la mano derecha a semiabierta si no quieres que quede en puño
    # _do_with_speed(["RHand"], [0.35], speed_main)

    # Regresar a NEUTRAL a la MISMA velocidad base
    neutral_user_match_speed(speed_main)

prep()
anim_satisfaction_v2()  
restore()