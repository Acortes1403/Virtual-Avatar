from flask import Flask, render_template, Response, jsonify, request, stream_with_context
import qi
import threading
import logging
import time
import os
import subprocess
from PIL import Image
import io
from flask_limiter import Limiter
import traceback
import time  
# Configure environment variables for localization
os.environ['LC_ALL'] = 'en_US.UTF-8'
os.environ['LANG'] = 'en_US.UTF-8'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("pepper_server.log"),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)
limiter = Limiter(app, key_func=lambda: "global")  # Rate limiter for API calls

# Global variables for thread safety and state
lock = threading.Lock()
audio_process = None
is_streaming = False

# Connect to Pepper's session
session = qi.Session()

def connect_to_pepper():
    """Attempt to connect to Pepper with retries."""
    connected = False
    while not connected:
        try:
            session.connect("tcp://127.0.0.1:9559")
            connected = True
            logging.info("Connected to Pepper's session.")
        except RuntimeError as e:
            logging.error("Cannot connect to Pepper: %s", e)
            logging.info("Retrying in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            logging.error("Unexpected error: %s", e)
            time.sleep(5)

connect_to_pepper()

def initialize_pepper():
    """Initialize Pepper's services and ensure it's ready for interaction."""
    global motion_service, autonomous_life_service, tts_service, video_service, audio_service
    try:
        # Retrieve required services
        autonomous_life_service = session.service("ALAutonomousLife")
        logging.info("ALAutonomousLife service initialized.")
        
        motion_service = session.service("ALMotion")
        logging.info("ALMotion service initialized.")
        
        tts_service = session.service("ALTextToSpeech")
        logging.info("ALTextToSpeech service initialized.")
        
        video_service = session.service("ALVideoDevice")
        logging.info("ALVideoDevice service initialized.")
        
        audio_service = session.service("ALAudioDevice")
        logging.info("ALAudioDevice service initialized.")
        
        # Disable autonomous life and wake up Pepper
        autonomous_life_service.setState("disabled")
        motion_service.wakeUp()
        logging.info("Pepper is awake and autonomous life is disabled.")
    except Exception as e:
        logging.error("Error initializing Pepper: %s", e)
        raise e


initialize_pepper()

def perform_action_with_animated_speech(action):
    """Perform predefined actions with natural animations and speech."""
    try:
        animated_speech_service = session.service("ALAnimatedSpeech")

        if action == 'greet':
            animated_speech_service.say(
                "Hello! ^start(animations/Stand/Gestures/Hey_1) I am Pepper. Nice to meet you!")
            return jsonify({'status': 'success', 'message': 'Greet action performed.'})

        elif action == 'presentation':
            animated_speech_service.say(
                "^start(animations/Stand/Gestures/Explain_1) Hello! My name is Pepper. "
                "I am a humanoid robot designed to assist and interact with people. "
                "^start(animations/Stand/Gestures/ShowTablet_1) "
                "I can move, talk, and interact with you in many ways. "
                "^start(animations/Stand/Gestures/CalmDown_1) "
                "Let us explore the future together!"
            )
            return jsonify({'status': 'success', 'message': 'Presentation completed.'})

        elif action == 'home':
            animated_speech_service.say("^start(animations/Stand/Gestures/CalmDown_1) Returning to my default position.")
            return jsonify({'status': 'success', 'message': 'Returned to home position.'})

        return jsonify({'status': 'error', 'message': 'Unknown action.'}), 400

    except Exception as e:
        logging.error("Error in animated speech: %s", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/video_feed')
def video_feed():
    """Route for Pepper's video feed."""
    return Response(gen_video_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

def gen_video_stream():
    """Generate a video stream from Pepper's camera."""
    global name_id
    try:
        name_id = video_service.subscribeCamera("python_client", 0, 2, 11, 15)
        while True:
            nao_image = video_service.getImageRemote(name_id)
            if nao_image:
                image = Image.frombytes("RGB", (nao_image[0], nao_image[1]), bytes(nao_image[6]))
                img_io = io.BytesIO()
                image.save(img_io, 'JPEG')
                img_io.seek(0)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + img_io.read() + b'\r\n')
            else:
                logging.warning("No image received.")
    except Exception as e:
        logging.error("Error in video streaming: %s", e)
    finally:
        if name_id:
            video_service.unsubscribe(name_id)
            logging.info("Camera unsubscribed.")

@app.route('/move_joint', methods=['POST'])
@limiter.limit("10 per second")
def move_joint():
    """API endpoint to move Pepper's joints."""
    data = request.get_json()
    joint = data.get('joint')
    angle = data.get('angle')
    speed = data.get('speed', 0.1)
    if not joint or angle is None:
        return jsonify({'status': 'error', 'message': 'Invalid parameters'}), 400
    try:
        motion_service.setAngles(joint, float(angle), float(speed))
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        logging.error("Error moving joint: %s", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/say', methods=['POST'])
@limiter.limit("5 per second")
def say_text():
    """API endpoint to make Pepper speak."""
    data = request.get_json()
    text = data.get('text', '')
    if not text:
        return jsonify({'status': 'error', 'message': 'No text provided'}), 400
    try:
        tts_service.say(text)
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        logging.error("Error in TTS: %s", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/')
def index():
    """Serve the main HTML page."""
    return render_template('index.html')
@app.route('/perform_action', methods=['POST'])
def perform_action():
    """Handle predefined actions sent from the frontend."""
    data = request.get_json()
    action = data.get('action', '')

    if not action:
        return jsonify({'status': 'error', 'message': 'No action provided'}), 400

    # Use the function `perform_action_with_animated_speech` to handle the action
    return perform_action_with_animated_speech(action)
# Route to start streaming audio
@app.route('/audio_feed')
def audio_feed():
    """Stream audio from Pepper's microphone."""
    return Response(generate_audio(), mimetype="audio/wav")

def generate_audio():
    """Generate audio stream using arecord."""
    global audio_process
    with lock:
        if audio_process is None:
            audio_process = subprocess.Popen(
                ["arecord", "-f", "S16_LE", "-r", "16000", "-c", "1"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
    try:
        while True:
            audio_chunk = audio_process.stdout.read(4096)
            if not audio_chunk:
                logging.warning("No audio data received.")
                yield b'\x00' * 4096  # Send silent data to keep stream alive
            yield audio_chunk
    except Exception as e:
        logging.error("Error in audio stream: %s", e)
    finally:
        stop_audio_process()

def stop_audio_process():
    """Stop the audio process if running."""
    global audio_process
    with lock:
        if audio_process:
            audio_process.terminate()
            audio_process = None
            logging.info("Audio process stopped.")

@app.route('/stop_audio', methods=['POST'])
def stop_audio():
    """API endpoint to stop audio streaming."""
    stop_audio_process()
    return jsonify({'status': 'success', 'message': 'Audio process stopped.'})

from flask import Flask, render_template, Response, jsonify, request
import qi
import threading
import logging
import time
import os
import subprocess
from PIL import Image
import io
from flask_limiter import Limiter
import traceback

# Configure environment variables for localization
os.environ['LC_ALL'] = 'en_US.UTF-8'
os.environ['LANG'] = 'en_US.UTF-8'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("pepper_server.log"),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)
limiter = Limiter(app, key_func=lambda: "global")  # Rate limiter for API calls

# Global variables for thread safety and state
lock = threading.Lock()
audio_process = None
is_streaming = False

# Connect to Pepper's session
session = qi.Session()

def connect_to_pepper():
    """Attempt to connect to Pepper with retries."""
    connected = False
    while not connected:
        try:
            session.connect("tcp://127.0.0.1:9559")
            connected = True
            logging.info("Connected to Pepper's session.")
        except RuntimeError as e:
            logging.error("Cannot connect to Pepper: %s", e)
            logging.info("Retrying in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            logging.error("Unexpected error: %s", e)
            time.sleep(5)

connect_to_pepper()

def initialize_pepper():
    """Initialize Pepper's services and ensure it's ready for interaction."""
    global motion_service, autonomous_life_service, tts_service, video_service, audio_service
    try:
        # Retrieve required services
        autonomous_life_service = session.service("ALAutonomousLife")
        logging.info("ALAutonomousLife service initialized.")
        
        motion_service = session.service("ALMotion")
        logging.info("ALMotion service initialized.")
        
        tts_service = session.service("ALTextToSpeech")
        logging.info("ALTextToSpeech service initialized.")
        
        video_service = session.service("ALVideoDevice")
        logging.info("ALVideoDevice service initialized.")
        
        audio_service = session.service("ALAudioDevice")
        logging.info("ALAudioDevice service initialized.")
        
        # Disable autonomous life and wake up Pepper
        autonomous_life_service.setState("disabled")
        motion_service.wakeUp()
        logging.info("Pepper is awake and autonomous life is disabled.")
    except Exception as e:
        logging.error("Error initializing Pepper: %s", e)
        raise e


initialize_pepper()

def perform_action_with_animated_speech(action):
    """Perform predefined actions with natural animations and speech."""
    try:
        animated_speech_service = session.service("ALAnimatedSpeech")

        if action == 'greet':
            animated_speech_service.say(
                "Hello! ^start(animations/Stand/Gestures/Hey_1) I am Pepper. Nice to meet you!")
            return jsonify({'status': 'success', 'message': 'Greet action performed.'})

        elif action == 'presentation':
            animated_speech_service.say(
                "^start(animations/Stand/Gestures/Explain_1) Hello! My name is Pepper. "
                "I am a humanoid robot designed to assist and interact with people. "
                "^start(animations/Stand/Gestures/ShowTablet_1) "
                "I can move, talk, and interact with you in many ways. "
                "^start(animations/Stand/Gestures/CalmDown_1) "
                "Let us explore the future together!"
            )
            return jsonify({'status': 'success', 'message': 'Presentation completed.'})

        elif action == 'home':
            animated_speech_service.say("^start(animations/Stand/Gestures/CalmDown_1) Returning to my default position.")
            return jsonify({'status': 'success', 'message': 'Returned to home position.'})

        return jsonify({'status': 'error', 'message': 'Unknown action.'}), 400

    except Exception as e:
        logging.error("Error in animated speech: %s", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/video_feed')
def video_feed():
    """Route for Pepper's video feed."""
    return Response(gen_video_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

def gen_video_stream():
    """Generate a video stream from Pepper's camera."""
    global name_id
    try:
        name_id = video_service.subscribeCamera("python_client", 0, 2, 11, 30)
        while True:
            nao_image = video_service.getImageRemote(name_id)
            if nao_image:
                image = Image.frombytes("RGB", (nao_image[0], nao_image[1]), bytes(nao_image[6]))
                img_io = io.BytesIO()
                image.save(img_io, 'JPEG')
                img_io.seek(0)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + img_io.read() + b'\r\n')
            else:
                logging.warning("No image received.")
    except Exception as e:
        logging.error("Error in video streaming: %s", e)
    finally:
        if name_id:
            video_service.unsubscribe(name_id)
            logging.info("Camera unsubscribed.")

@app.route('/move_joint', methods=['POST'])
@limiter.limit("10 per second")
def move_joint():
    """API endpoint to move Pepper's joints."""
    data = request.get_json()
    joint = data.get('joint')
    angle = data.get('angle')
    speed = data.get('speed', 0.1)
    if not joint or angle is None:
        return jsonify({'status': 'error', 'message': 'Invalid parameters'}), 400
    try:
        motion_service.setAngles(joint, float(angle), float(speed))
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        logging.error("Error moving joint: %s", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/say', methods=['POST'])
@limiter.limit("5 per second")
def say_text():
    """API endpoint to make Pepper speak."""
    data = request.get_json()
    text = data.get('text', '')
    if not text:
        return jsonify({'status': 'error', 'message': 'No text provided'}), 400
    try:
        tts_service.say(text)
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        logging.error("Error in TTS: %s", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/')
def index():
    """Serve the main HTML page."""
    return render_template('index.html')
@app.route('/perform_action', methods=['POST'])
def perform_action():
    """Handle predefined actions sent from the frontend."""
    data = request.get_json()
    action = data.get('action', '')

    if not action:
        return jsonify({'status': 'error', 'message': 'No action provided'}), 400

    # Use the function `perform_action_with_animated_speech` to handle the action
    return perform_action_with_animated_speech(action)
# Route to start streaming audio
@app.route('/audio_feed')
def audio_feed():
    """Stream audio from Pepper's microphone."""
    return Response(generate_audio(), mimetype="audio/wav")

def generate_audio():
    """Generate audio stream using arecord."""
    global audio_process
    with lock:
        if audio_process is None:
            audio_process = subprocess.Popen(
                ["arecord", "-f", "S16_LE", "-r", "16000", "-c", "1"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
    try:
        while True:
            audio_chunk = audio_process.stdout.read(4096)
            if not audio_chunk:
                logging.warning("No audio data received.")
                yield b'\x00' * 4096  # Send silent data to keep stream alive
            yield audio_chunk
    except Exception as e:
        logging.error("Error in audio stream: %s", e)
    finally:
        stop_audio_process()

def stop_audio_process():
    """Stop the audio process if running."""
    global audio_process
    with lock:
        if audio_process:
            audio_process.terminate()
            audio_process = None
            logging.info("Audio process stopped.")

@app.route('/stop_audio', methods=['POST'])
def stop_audio():
    """API endpoint to stop audio streaming."""
    stop_audio_process()
    return jsonify({'status': 'success', 'message': 'Audio process stopped.'})

@app.route('/execute_python', methods=['POST'])
@limiter.limit("2 per second")  # Limitar la cantidad de ejecuciones por segundo
def execute_python():
    """Endpoint para ejecutar cdigo Python personalizado."""
    data = request.get_json()
    code = data.get('code', '')

    if not code:
        return jsonify({'status': 'error', 'message': 'No code provided'}), 400

    safe_globals = {
        "__builtins__": None,
        "motion_service": motion_service,
        "tts_service": tts_service,
        "session": session,
        "logging": logging,
        "time": time,  # Agregado para permitir el uso de 'time'

    }

    try:
        exec(code, safe_globals)
        return jsonify({'status': 'success', 'message': 'Code executed successfully.'}), 200
    except Exception as e:
        error_message = traceback.format_exc()
        logging.error("Error executing Python code: %s", error_message)
        return jsonify({'status': 'error', 'message': error_message}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8070)