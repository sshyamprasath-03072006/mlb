import os
import flask
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.static_folder = 'static'
app.secret_key = os.urandom(24)  # Required for sessions

# Configure Gemini API
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# --- Utility Functions ---

def check_player_exists(player_name):
    prompt = f"Is there a baseball player named {player_name}? Answer with only 'yes' or 'no'."
    try:
        response = model.generate_content(prompt)
        answer = response.text.strip().lower()
        return answer == 'yes'
    except Exception as e:
        print(f"Error checking player existence: {e}")
        return False

def generate_initial_bio(player_name):
    prompt = f"Give me a short biography of baseball player {player_name} in under 75 words. Include notable achievements."
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error generating initial bio: {e}")
        return f"I'm {player_name}. I am a baseball player."

def generate_prompt(chat_history, player_name):
    base_prompt = f"You are {player_name}, a baseball player. Answer questions as you."
    context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
    full_prompt = f"{base_prompt}\n{context}\nmodel:"
    return full_prompt

# --- Route Handlers ---

def initialize_session():
    flask.session['player_name'] = None
    flask.session['chat_history'] = []
    flask.session['current_theme'] = 'light'

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'player_name' not in flask.session:
        initialize_session()

    player_name = flask.session['player_name']
    chat_history = flask.session['chat_history']
    current_theme = flask.session['current_theme']
    error_message = None

    if request.method == 'POST':
        if 'player_name_input' in request.form:
            player_name_input = request.form['player_name_input'].lower()
            if check_player_exists(player_name_input):
                flask.session['player_name'] = player_name_input
                chat_history.clear()
                player_name = player_name_input
                bio = generate_initial_bio(player_name)
                chat_history.append({"role": "model", "content": f"Hi, I am {player_name.title()}. {bio}"})
                flask.session['chat_history'] = chat_history
            else:
                error_message = "Player not found. Please enter a valid baseball player name."

        elif 'message' in request.form:
            message = request.form['message']
            chat_history.append({"role": "user", "content": message})
            player_name = flask.session['player_name']
            prompt = generate_prompt(chat_history, player_name)

            try:
                response = model.generate_content(prompt)
                ai_response = response.text.strip()
                chat_history.append({"role": "model", "content": ai_response})
            except Exception as e:
                ai_response = f"Error generating response: {e}"
                chat_history.append({"role": "model", "content": ai_response})

            flask.session['chat_history'] = chat_history

        elif 'toggle_theme' in request.form:
            current_theme = 'dark' if current_theme == 'light' else 'light'
            flask.session['current_theme'] = current_theme

    return render_template('index.html', player_name=player_name, chat_history=chat_history, current_theme=current_theme, error_message=error_message)


@app.route('/switch_theme', methods=['POST'])
def switch_theme():
    if 'current_theme' in flask.session:
        flask.session['current_theme'] = 'dark' if flask.session['current_theme'] == 'light' else 'light'
    else:
        flask.session['current_theme'] = 'dark'

    return jsonify({'theme': flask.session['current_theme']})


if __name__ == '__main__':
    app.run(debug=True)