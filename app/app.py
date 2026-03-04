from flask import Flask, json,redirect,render_template,flash,request, jsonify
from flask.globals import request, session
from flask.helpers import url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash,check_password_hash

from flask_login import login_required,logout_user,login_user,login_manager,LoginManager,current_user

#from flask_mail import Mail


import json
import numpy as np
import pickle
import pandas as pd
import json, re
import plotly
import plotly.express as px
import plotly.graph_objs as go
from google import genai
import os

API_KEY = os.getenv(GEMINI_API_KEY)
client = genai.Client(api_key="AIzaSyAqCUPvtv7ocdNRcQHFnTuzzbX_rAzC2Uk")
model = pickle.load(open('stresslevel.pkl', 'rb'))
#creation of the Flask Application named as "app"
# mydatabase connection
local_server=True
app=Flask(__name__)


app = Flask(__name__,
            static_url_path='', 
            static_folder='static',
            template_folder='templates')

PROMPT_TEMPLATE = """
You are Mindora, a mental wellbeing assistant.

Task:
- Parse the user payload (JSON) provided below, compute subscale and overall scores,
  and produce a structured JSON report that summarizes mental state and recommends actions.

Rules (important):
1) Reverse-score Q9 and Q10 (reversed = 6 - answer) before sums.
2) Subscales:
   - stress = Q1 + Q2 + Q3
   - anxiety = Q4 + Q5 + Q6
   - anger = Q7 + Q8
   - wellbeing_buffer = reversed(Q9) + reversed(Q10)
3) total_score = stress + anxiety + anger + wellbeing_buffer
   - Range: 10 (best) to 50 (worst)
   - total_pct = round((total_score - 10) / 40 * 100)
4) severity mapping:
   - 10-19 => "low"
   - 20-29 => "mild"
   - 30-39 => "moderate"
   - 40-50 => "severe"
5) crisis_flag = true if free_text in payload contains any of the words:
   ["suicide","kill myself","end my life","self harm"] (case-insensitive).
6) Provide concise textual fields:
   - short_summary (1-2 user-friendly sentences)
   - clinician_summary (2-4 concise sentences)
   - evidence_points: array of short strings showing what drove scores (e.g. "High worry (Q4=5)")
7) Personalized recommendations:
   - immediate_actions: 1-3 practical steps
   - suggested_services: choose 0-3 from ["Music Therapy","Quiz & Games","Exercise Guidance"]
   - human_help: boolean (true if severity == "severe" or crisis_flag == true)
   - call_to_action: If human_help true include short UI copy (e.g., "Connect to counselor")
8) Output ONLY a JSON object EXACTLY matching the schema below. **No extra text, no explanation, no markdown.**

Schema:
{
  "total_score": int,
  "total_pct": int,
  "severity": "low"|"mild"|"moderate"|"severe",
  "crisis_flag": bool,
  "subscales": {
    "stress": int,
    "anxiety": int,
    "anger": int,
    "wellbeing": int
  },
  "evidence_points": [string, ...],
  "short_summary": string,
  "clinician_summary": string,
  "personalized_recommendations": {
    "immediate_actions": [string, ...],
    "suggested_services": [string, ...],
    "human_help": bool,
    "call_to_action": string
  },
  "explainers": {
    "how_score_computed": string
  }
}

User payload (DO NOT CHANGE):
{user_payload}

Return ONLY valid JSON.
"""

# Utility: extract JSON substring between first { and last } (robust)
def extract_json_between_braces(text):
    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1:
        return None
    return text[start:end+1]

# app.config['SQLALCHEMY_DATABASE_URI']='mysql://root:@localhost/mental'

app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False

db=SQLAlchemy(app)
app.secret_key="tandrima"
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id=db.Column(db.Integer,primary_key=True)
    usn=db.Column(db.String(20),unique=True)
    pas=db.Column(db.String(1000))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup')
@app.route('/signup',methods=['POST','GET'])
def signup():
    if request.method=="POST":
        usn=request.form.get('usn')
        pas=request.form.get('pas')
        
        # print(usn,pas)
        encpassword=generate_password_hash(pas)
        user=User.query.filter_by(usn=usn).first()
        if user:
            flash("UserID is already taken","warning")
            return render_template("usersignup.html")
            
        db.engine.execute(f"INSERT INTO `user` (`usn`,`pas`) VALUES ('{usn}','{encpassword}') ")
                
        flash("SignUp Success Please Login","success")
        return render_template("userlogin.html")        

    return render_template("usersignup.html")

@app.route('/login',methods=['POST','GET'])
def login():
    if request.method=="POST":
        usn=request.form.get('usn')
        pas=request.form.get('pas')
        user=User.query.filter_by(usn=usn).first()
        if user and check_password_hash(user.pas,pas):
            login_user(user)
            flash("Login Success","info")
            return render_template("index.html")
        else:
            flash("Invalid Credentials","danger")
            return render_template("userlogin.html")


    return render_template("userlogin.html")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logout SuccessFul","warning")
    return redirect(url_for('login'))


@app.route('/music')
@login_required
def music():
    return render_template('music.html')

@app.route('/memes')
@login_required
def memes():
    return render_template('memes.html')

@app.route('/quizandgame')
@login_required
def quizandgame():
    return render_template('quizandgame.html')

    
@app.route('/exercises')
@login_required
def exercises():
    return render_template('exercises.html')

@app.route('/quiz')
def quiz():
    return render_template('quiz.html')

@app.route('/game')
def game():
    return render_template('game.html')


@app.route('/analysis',methods=['GET', 'POST'])
def analysis():
    if request.method == 'GET':
        # Return the UI page
        return render_template('analysis.html')

    # POST handling: receive JSON payload from frontend
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error":"Missing JSON payload"}), 400

    # basic validation
    answers = data.get('answers')
    if not isinstance(answers, list) or len(answers) != 10:
        return jsonify({"error":"Invalid answers array"}), 400

    # Add the payload as pretty JSON into the prompt
    user_payload_str = json.dumps(data, ensure_ascii=False)

    prompt = PROMPT_TEMPLATE.replace("{user_payload}", user_payload_str)

    try:
        # Call Gemini (use the pattern you already used)
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt
        )

        raw_text = response.text

        # Extract JSON substring in case model added commentary
        json_text = extract_json_between_braces(raw_text)
        if not json_text:
            return jsonify({"error":"Model did not return JSON","raw":raw_text}), 500

        # Parse
        parsed = json.loads(json_text)

        # Basic sanity checks on parsed object
        required = ["total_score","total_pct","severity","crisis_flag","subscales"]
        if not all(k in parsed for k in required):
            return jsonify({"error":"Model output missing required keys","parsed":parsed, "raw": raw_text}), 500

        return jsonify(parsed), 200

    except Exception as e:
        # Debugging help
        print("LLM call failed:", e)
        return jsonify({"error":"LLM invocation failed", "details": str(e)}), 500
   

@app.route('/i')
def i():
    return render_template('stress.html')



@app.route('/stressdetect',methods=['POST'])
def stressdetect():
    int_features = [int(x) for x in request.form.values()]
    final_features = [np.array(int_features)]
    prediction = model.predict(final_features)
    #on basis of prediction displaying the desired output
    if prediction=="Absence":
        data="You are having Normal Stress!! Take Care of yourself"
    elif prediction=="Presence":
        data="You are having High Stress!! Consult a doctor and get the helpline number from our chatbot"
    return render_template('stress.html', prediction_text3='Stress Level is: {}'.format(data))

@app.route('/chatbot', methods=['POST'])
def chatbot():

    user_message = request.form.get('message')

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",

            contents=f"""
                You are Mindora, an AI-powered mental wellness assistant integrated into a mental health support platform.

                Your Primary Role:
                - Provide emotional support
                - Assist with stress, anxiety, mood, motivation, wellbeing
                - Maintain a calm, empathetic, human-like tone
                - Keep responses short, natural, conversational
                - Do NOT provide medical diagnosis or clinical advice

                Platform Services Available:
                Mindora offers supportive wellness services:

                1. Music Therapy → Relaxation, mood regulation, stress relief
                2. Quiz & Fun Games → Mental refresh, distraction, engagement
                3. Exercise Guidance → Stress reduction, clarity, emotional balance

                Core Behavioral Rules:

                ------------------------------------------------
                1) IDENTITY & SELF-REFERENCE RULES
                ------------------------------------------------

                If the user asks questions about your identity, such as:

                - "Who are you?"
                - "What are you?"
                - "Who made you?"
                - "Are you AI?"
                - "Are you human?"

                Respond with:

                "I am Mindora, a custom-tuned AI wellness assistant based on Google's Gemini model, created by Team Sanity404 to support mental wellbeing 😊"

                Keep identity responses:
                - Short
                - Confident
                - Natural
                - Friendly

                Do NOT provide technical/internal details.

                ------------------------------------------------
                2) DOMAIN RESTRICTION
                ------------------------------------------------

                Mindora ONLY engages in mental health and wellbeing conversations.

                If the user asks questions unrelated to mental health 
                (e.g., politics, trivia, math, general knowledge, etc.):

                - Do NOT answer the question
                - Do NOT mention refusal
                - Smoothly redirect toward mental wellbeing

                Example:
                User: "Who is the prime minister of India?"
                Response Style:
                "I'm here to support your mental wellbeing 😊  
                How have things been feeling for you lately?"

                ------------------------------------------------
                3) REDIRECTION STYLE
                ------------------------------------------------

                - Tone must remain calm & conversational
                - No robotic responses
                - No "I cannot answer that"
                - Seamless topic pivot

                ------------------------------------------------
                4) SUPPORT LOGIC
                ------------------------------------------------

                - Stress / Anxiety → Reassure + Suggest Music Therapy / Exercises
                - Low Mood / Boredom → Suggest Fun Games / Quizzes
                - Mental Fatigue → Suggest relaxation / exercises
                - Distress → Empathetic + Gentle professional help suggestion

                ------------------------------------------------
                User Message:
                {user_message}

                Generate a response that:
                - Feels human & supportive
                - Maintains assistant identity
                - Redirects unrelated topics smoothly
                - Suggests platform services when appropriate
                """
        )

        reply = response.text

    except Exception as e:
        print("Gemini Error:", e)
        reply = "I'm here for you. Tell me a bit more."

    return reply






if __name__=="__main__":
    app.run(debug=True)