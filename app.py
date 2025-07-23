from flask import Flask, request, jsonify, send_from_directory
import requests
from twilio.twiml.messaging_response import MessagingResponse
from twilio.twiml.voice_response import VoiceResponse
from google.oauth2 import service_account
from googleapiclient.discovery import build
import openai
import os

print("OPENAI_API_KEY loaded is:", os.environ.get("OPENAI_API_KEY"))
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
app = Flask(__name__)

# Google Calendar API setup
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = os.environ.get('GOOGLE_CREDENTIALS_PATH', 'austin-hybrid-receptionist-aa8eaffad54b.json')
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
calendar_service = build('calendar', 'v3', credentials=credentials)

# Load knowledge base
with open('knowledge_base.txt', 'r') as f:
    knowledge_base = f.read()

openai.api_key = os.environ.get("OPENAI_API_KEY")

def process_with_llm(message):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"Knowledge base: {knowledge_base}\nYou are a helpful receptionist for Austin Hybrid Battery."},
                {"role": "user", "content": message}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print("OpenAI Exception:", str(e))
        return f"Error contacting LLM: {str(e)}"


def transcribe_recording(recording_url):
    """Call external Whisper API for speech-to-text."""
    whisper_url = os.environ.get('WHISPER_API_URL', 'https://2970-35-227-126-138.ngrok-free.app/transcribe')
    try:
        response = requests.post(whisper_url, json={'recording_url': recording_url})
        return response.json().get('transcription', 'Sorry, I couldn’t transcribe the audio.')
    except Exception as e:
        return f"Error transcribing: {str(e)}"

def text_to_speech(text):
    """Call external gTTS API for text-to-speech."""
    tts_url = os.environ.get('TTS_API_URL', 'https://2970-35-227-126-138.ngrok-free.app/tts')
    try:
        response = requests.post(tts_url, json={'text': text})
        audio_url = response.json().get('audio_url')
        return audio_url
    except Exception as e:
        return f"Error generating speech: {str(e)}"

def handle_appointment(message):
    """Book an appointment in Google Calendar (simplified for POC)."""
    event = {
        'summary': 'Hybrid Battery Appointment',
        'start': {'dateTime': '2025-07-10T10:00:00', 'timeZone': 'America/Chicago'},
        'end': {'dateTime': '2025-07-10T11:00:00', 'timeZone': 'America/Chicago'},
    }
    event = calendar_service.events().insert(calendarId='primary', body=event).execute()
    return f"Appointment booked for 10:00 AM on July 10, 2025. Event ID: {event.get('id')}"

# Chat endpoint
@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json['message']
    if "appointment" in user_message.lower() or "schedule" in user_message.lower():
        response = handle_appointment(user_message)
    else:
        response = process_with_llm(user_message)
    return jsonify({'response': response})

# SMS endpoint
@app.route('/sms', methods=['POST'])
def sms():
    user_message = request.values.get('Body', '')
    if "appointment" in user_message.lower() or "schedule" in user_message.lower():
        response = handle_appointment(user_message)
    else:
        response = process_with_llm(user_message)
    twiml = MessagingResponse()
    twiml.message(response)
    return str(twiml)

# Phone call endpoint
@app.route('/voice', methods=['POST'])
def voice():
    resp = VoiceResponse()
    resp.say("Welcome to Austin Hybrid Battery. How can I assist you today?", voice='alice')
    resp.record(action='/handle-recording', method='POST')
    return str(resp)

# Handle recorded phone input
@app.route('/handle-recording', methods=['POST'])
def handle_recording():
    recording_url = request.values.get('RecordingUrl', '')
    transcription = transcribe_recording(recording_url)
    if "appointment" in transcription.lower() or "schedule" in transcription.lower():
        response = handle_appointment(transcription)
    else:
        response = process_with_llm(transcription)
    speech_url = text_to_speech(response)
    resp = VoiceResponse()
    resp.play(speech_url)
    return str(resp)

# Serve static files (e.g., audio responses)
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
