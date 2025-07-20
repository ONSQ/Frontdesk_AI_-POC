### Complete Step-by-Step Instructions to Set Up Frontdesk AI POC Locally on Your Laptop with Docker and API Calls

This guide consolidates everything needed to get your Austin Hybrid Battery front desk AI POC running on your local laptop. It uses Docker for containerization (isolating the app), integrates API calls for LLM (ChatGPT), transcription (Whisper), TTS (text-to-speech), Google Calendar, and Twilio (for SMS/voice). The setup leverages OpenAI for simplified AI processing (no separate local servers needed), and ngrok to expose the app for Twilio webhooks.

The entire process should take 1-2 hours if you're comfortable with terminals; longer if new to Docker. This is tailored for your July 25, 2025 deadline—testable by tomorrow (July 20, 2025). If errors occur, note the exact message and share for troubleshooting.

#### Step 1: Prerequisites and Environment Setup
1. **Install Required Software**:
   - **Python 3.10+**: Download from python.org if not installed. Verify: `python --version`.
   - **Docker**: Install Docker Desktop from docker.com (includes Docker Compose). Start the app and verify: `docker --version`.
   - **ngrok**: Sign up free at ngrok.com, download the executable, unzip, and authenticate: `./ngrok authtoken your_ngrok_authtoken` (get token from dashboard). Verify: `./ngrok http 80` (stop with Ctrl+C).
   - **API Accounts and Keys**:
     - **OpenAI**: Sign up at openai.com, get an API key (free tier or add $5-10 credit). Note: Usage costs ~$0.01-0.10 per interaction.
     - **Google Calendar**: In console.cloud.google.com, create a project, enable Calendar API, create a service account (grant "Editor" role), download JSON key (e.g., `austin-hybrid-receptionist-aa8eaffad54b.json`). Share your calendar with the service account email.
     - **Twilio**: Sign up at twilio.com (free trial with $15 credit), get Account SID/Auth Token, buy a phone number. Note your Twilio phone number for testing.

2. **Project Files Preparation**:
   - Ensure your project directory (`Frontdesk_AI_-POC-main`) contains:
     - `app.py` (updated code below; copy-paste this into the file).
     - `requirements.txt` (updated below; copy-paste).
     - `knowledge_base.txt` (provided in your upload).
     - `austin-hybrid-receptionist-aa8eaffad54b.json` (Google key; place in root).
     - `.gitignore` (provided; optional but good for ignoring temp files).
   - Create a `static` folder in the root (for TTS audio files).
   - Updated `requirements.txt` (add/replace with this for compatibility):
     ```
     flask==2.0.1
     twilio==7.12.0
     google-auth==2.40.3
     google-api-python-client==2.52.0
     requests==2.28.1
     openai==0.28.0  # For OpenAI API
     gunicorn==20.1.0  # Production server for Docker
     dateparser==1.2.0  # For parsing dates in appointments
     ```
   - Install locally (for testing outside Docker): Create/activate venv (`python -m venv venv; source venv/bin/activate`), then `pip install -r requirements.txt`.

3. **Update `app.py`**:
   Copy-paste this full code into `app.py` (integrates OpenAI directly for LLM/STT/TTS, handles appointments dynamically):
   ```python
   from flask import Flask, request, jsonify, send_from_directory
   from twilio.twiml.messaging_response import MessagingResponse
   from twilio.twiml.voice_response import VoiceResponse
   from google.oauth2 import service_account
   from googleapiclient.discovery import build
   import os
   import openai
   from io import BytesIO
   import dateparser
   from datetime import timedelta
   import requests

   app = Flask(__name__)

   # Google Calendar setup
   SCOPES = ['https://www.googleapis.com/auth/calendar']
   SERVICE_ACCOUNT_FILE = os.environ.get('GOOGLE_CREDENTIALS_PATH', 'austin-hybrid-receptionist-aa8eaffad54b.json')
   credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
   calendar_service = build('calendar', 'v3', credentials=credentials)

   # Load knowledge base
   with open('knowledge_base.txt', 'r') as f:
       knowledge_base = f.read()

   # OpenAI setup
   openai.api_key = os.environ.get('OPENAI_API_KEY')

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
           return f"Error with LLM: {str(e)}"

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

   @app.route('/voice', methods=['POST'])
   def voice():
       resp = VoiceResponse()
       resp.say("Welcome to Austin Hybrid Battery. How can I assist you today?", voice='alice')
       resp.record(action='/handle-recording', method='POST')
       return str(resp)

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

   @app.route('/static/<path:filename>')
   def static_files(filename):
       return send_from_directory('static', filename)

   if __name__ == '__main__':
       port = int(os.environ.get('PORT', 8080))
       app.run(host='0.0.0.0', port=port, debug=False)
   ```

#### Step 2: Create Dockerfile
Create a new file `Dockerfile` in the root:
```
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
```

#### Step 3: Build and Run the Docker Container
1. Build the image:
   ```
   docker build -t frontdesk-ai-poc .
   ```
2. Run the container (pass env vars; mount JSON and static for persistence):
   ```
   docker run -d -p 8080:8080 \
     -v $(pwd)/austin-hybrid-receptionist-aa8eaffad54b.json:/app/austin-hybrid-receptionist-aa8eaffad54b.json \
     -v $(pwd)/static:/app/static \
     --env OPENAI_API_KEY=your_openai_api_key_here \
     --env GOOGLE_CREDENTIALS_PATH=/app/austin-hybrid-receptionist-aa8eaffad54b.json \
     --name frontdesk-ai \
     frontdesk-ai-poc
   ```
   - Check status: `docker ps`. Logs: `docker logs frontdesk-ai`.

#### Step 4: Expose with ngrok and Configure Twilio
1. Start ngrok: `./ngrok http 8080` (note the public URL, e.g., https://abcd.ngrok-free.app).
2. In Twilio console:
   - SMS webhook: https://abcd.ngrok-free.app/sms (HTTP POST).
   - Voice webhook: https://abcd.ngrok-free.app/voice (HTTP POST).

#### Step 5: Test the Setup
1. **Local Chat**: `curl -X POST http://localhost:8080/chat -H "Content-Type: application/json" -d '{"message": "What services do you offer?"}'`.
2. **SMS**: Text "Schedule appointment for next Tuesday at 10 AM" to your Twilio number.
3. **Voice**: Call Twilio number, say "Book a diagnostic for tomorrow"; listen for response.
4. **Appointment Check**: View in Google Calendar; confirm event added.
5. Stop: `docker stop frontdesk-ai`. Restart: `docker start frontdesk-ai`.

#### Troubleshooting
- **Docker Build Fails**: Ensure files are in root; try `docker build --no-cache -t frontdesk-ai-poc .`.
- **API Errors**: Verify env vars (`docker exec -it frontdesk-ai env`); check OpenAI/Twilio dashboards for logs.
- **ngrok Changes**: Restart ngrok and update Twilio if URL expires.
- **Performance**: If slow, upgrade to "gpt-4o-mini" in code. For prod, consider Groq for faster/free LLM.

This is fully local, self-contained, and ready for your needs. If anything's unclear, provide details!
