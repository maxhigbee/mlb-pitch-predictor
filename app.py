from flask import Flask, render_template, request, jsonify
import requests
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import my_functions  # your pitch functions in a separate file


app = Flask(__name__)

@app.route("/healthz")
def healthz():
    return "OK", 200

def get_date():
    eastern = ZoneInfo("America/New_York")
    return datetime.now(eastern).strftime("%Y-%m-%d")


@app.route('/live_games', methods=['GET'])
def live_games():
   today = get_date()
   schedule_url = f'https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate={today}&endDate={today}'
   raw_data = requests.get(schedule_url)
   cleaned_data = raw_data.json()
   live_games_list = []
   for date in cleaned_data['dates']:
       for game in date['games']:
           if game['status']['detailedState'] == 'In Progress':
               live_games_list.append({
                   "gamePk": game['gamePk'],
                   "away_team": game['teams']['away']['team']['name'],
                   "home_team": game['teams']['home']['team']['name']
               })
   if not live_games_list:
       return jsonify(message="No live games currently."), 200
   return jsonify(live_games_list)


@app.route('/predict_pitch', methods=['GET'])
def predict_pitch_route():
   game_id = request.args.get('game_id')
   if not game_id:
       return jsonify(error="Missing game_id"), 400
   try:
       # Ensure game_id is an integer
       result = my_functions.predict_pitch_once(int(game_id))
       return jsonify(result)


   except Exception as e:
       # Log the exception for debugging
       print(f"Error on /predict_pitch: {e}")
       return jsonify(error=str(e)), 500


@app.route('/')
def home():
   return render_template('index.html')


if __name__ == '__main__':
   app.run(debug=True)