from flask import Flask, request, jsonify, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
from twilio.twiml.voice_response import VoiceResponse
from google.oauth2 import service_account
from googleapiclient.discovery import build
import openai
import os
import openai
from io import BytesIO
import dateparser
from datetime import timedelta
import requests

print("OPENAI_API_KEY loaded is:", os.environ.get("OPENAI_API_KEY"))
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
app = Flask(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = os.environ.get('GOOGLE_CREDENTIALS_PATH', 'austin-hybrid-receptionist-aa8eaffad54b.json')
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
calendar_service = build('calendar', 'v3', credentials=credentials)

with open('knowledge_base.txt', 'r') as f:
    knowledge_base = f.read()

<<<<<<< HEAD
openai.api_key = os.environ.get("OPENAI_API_KEY")
=======
openai.api_key = os.environ.get('OPENAI_API_KEY')
>>>>>>> b67221c6db8161810f7a38f89907ebdb2c39cc02

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
<<<<<<< HEAD
        print("OpenAI Exception:", str(e))
        return f"Error contacting LLM: {str(e)}"
=======
        return f"Error with LLM: {str(e)}"
>>>>>>> b67221c6db8161810f7a38f89907ebdb2c39cc02


def transcribe_recording(recording_url):
    try:
        audio_response = requests.get(recording_url)
        audio_file = BytesIO(audio_response.content)
        audio_file.name = "recording.wav"
        transcription = openai.Audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
        return transcription.text
    except Exception as e:
        return f"Error transcribing: {str(e)}"

def text_to_speech(text):
    try:
        response = openai.Audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text
        )
        audio_path = "static/response.mp3"
        response.stream_to_file(audio_path)
        return "/static/response.mp3"
    except Exception as e:
        return f"Error generating speech: {str(e)}"

def handle_appointment(message):
    parsed_date = dateparser.parse(message, settings={'PREFER_DATES_FROM': 'future'})
    if not parsed_date:
        return "Please specify a date and time for the appointment."
    start_time = parsed_date.isoformat()
    end_time = (parsed_date + timedelta(hours=1)).isoformat()
    event = {
        'summary': 'Hybrid Battery Appointment',
        'start': {'dateTime': start_time, 'timeZone': 'America/Chicago'},
        'end': {'dateTime': end_time, 'timeZone': 'America/Chicago'},
    }
    event = calendar_service.events().insert(calendarId='primary', body=event).execute()
    return f"Appointment booked for {parsed_date.strftime('%I:%M %p on %B %d, %Y')}. Event ID: {event.get('id')}"

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json['message']
    if "appointment" in user_message.lower() or "schedule" in user_message.lower():
        response = handle_appointment(user_message)
    else:
        response = process_with_llm(user_message)
    return jsonify({'response': response})

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
