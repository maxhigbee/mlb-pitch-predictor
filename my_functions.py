import requests
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ----------------------------
# Helper function: get today's date
# ----------------------------


def get_date():
    western = ZoneInfo("America/Seattle")
    return datetime.now(western).strftime("%Y-%m-%d")


# ----------------------------
# Helper function: get pitch-by-pitch pitcher history
# ----------------------------
def get_pitcher_data(pitcher_id, start_date, end_date):
   from pybaseball import statcast_pitcher
   import io
   import contextlib


   try:
       # Suppress print output from pybaseball
       f = io.StringIO()
       with contextlib.redirect_stdout(f):
           data = statcast_pitcher(start_dt=start_date, end_dt=end_date, player_id=pitcher_id)


       if data.empty:
           return None


       # Keep only regular season games
       data = data[data['game_type'] == 'R'].copy()
       if data.empty:
           return None


       # Prepare dataframe
       required_cols = [
           'balls', 'strikes', 'outs_when_up', 'fld_score', 'bat_score', 'inning',
           'pitch_type', 'stand', 'game_pk', 'at_bat_number'
       ]
       df = data[required_cols].copy()
       df['margin'] = df['fld_score'] - df['bat_score']
       df['last_pitch_type'] = df.groupby(['game_pk', 'at_bat_number'])['pitch_type'].shift(-1)
       df['last_pitch_type'] = df['last_pitch_type'].fillna('N/A')


       df.rename(columns={'outs_when_up': 'outs', 'stand': 'bat_side'}, inplace=True)


       final_cols = [
           'game_pk', 'at_bat_number', 'balls', 'strikes', 'outs', 'margin',
           'inning', 'last_pitch_type', 'pitch_type', 'bat_side'
       ]


       final_df = df[final_cols]
       final_df.reset_index(drop=True, inplace=True)


       return final_df


   except Exception as e:
       print(f"Error in get_pitcher_data: {e}")
       return None


# ----------------------------
# Helper function: get current game state
# ----------------------------
def get_game_data(game_id):
   pitch_data_dict = {
       'last_pitch_type': [],
       'current_pitcher': [],
       'balls': [],
       'strikes': [],
       'outs': [],
       'bat_side': [],
       'inning': [],
       'margin': [],
       'last_ab': [],
       'home_score': [],
       'away_score': []
   }


   try:
       scrape_url = f'https://statsapi.mlb.com/api/v1.1/game/{game_id}/feed/live/diffPatch'
       live_data = requests.get(scrape_url).json()


       last_ab = live_data['liveData']['plays']['allPlays'][-1]
       pitch_data_dict['last_ab'].append(last_ab)

       balls = last_ab['count']['balls']
       strikes = last_ab['count']['strikes']
       outs = last_ab['count']['outs']
       bat_side = last_ab['matchup']['batSide']['description']
       inning = last_ab['about']['inning']

       for play_event in live_data['liveData']['plays']['allPlays']:
         for event in play_event['playEvents']:
           try:
             last_pitch_type = event['details']['type']['code']
           except:
             continue
          

       if balls == 0 and strikes == 0:
           last_pitch_type = 'N/A'


       pitch_data_dict['last_pitch_type'].append(last_pitch_type)
       pitch_data_dict['current_pitcher'].append(last_ab['matchup']['pitcher']['id'])
       pitch_data_dict['balls'].append(balls)
       pitch_data_dict['strikes'].append(strikes)
       pitch_data_dict['outs'].append(outs)
       pitch_data_dict['bat_side'].append(bat_side)
       pitch_data_dict['inning'].append(inning)


       if last_ab['about']['halfInning'] == 'top':
           pitch_data_dict['margin'].append(last_ab['result']['homeScore'] - last_ab['result']['awayScore'])
       else:
           pitch_data_dict['margin'].append(last_ab['result']['awayScore'] - last_ab['result']['homeScore'])


       pitch_data_dict['home_score'].append(last_ab['result']['homeScore'])
       pitch_data_dict['away_score'].append(last_ab['result']['awayScore'])


       pitch_data = pd.DataFrame(pitch_data_dict)
       return pitch_data


   except Exception as e:
       print(f"Error in get_game_data: {e}")
       return None


# ----------------------------
# Main function: predict next pitch once
# ----------------------------
def predict_pitch_once(game_id):
  
   current_state = get_game_data(game_id)
   if current_state is None or current_state.empty:
       return {"error": "Could not get current game data."}


   pitcher_id = int(current_state['current_pitcher'][0])


   today_obj = datetime.strptime(get_date(), "%Y-%m-%d")
   yesterday_obj = today_obj - timedelta(days=1)
   yesterday = yesterday_obj.strftime("%Y-%m-%d")
   starting_day = f"{today_obj.year}-03-01"

   k = 98
   pitcher_history_df = get_pitcher_data(pitcher_id, starting_day, yesterday)
   if pitcher_history_df is None or len(pitcher_history_df) < k:
       return {"error": "Not enough historical data for this pitcher."}


   # Convert bat sides to numeric
   pitcher_history_df['bat_side'] = pitcher_history_df['bat_side'].apply(lambda x: 0 if x == "L" else 1)
   current_state['bat_side'] = current_state['bat_side'].apply(lambda x: 0 if x == "Left" else 1)


   # Features and scoring
   features = ['last_pitch_type', 'balls', 'strikes', 'outs', 'inning', 'bat_side']

   feature_weights = {
       'last_pitch_type': 1.03, 
       'balls': 1.379,
       'strikes': 1.948,
       'outs': 2.33,
       'inning': 2.97, 
       'bat_side': 1.971
   }

   def score_row(row):
       score = 0
       for feature in features:
           row_value = row.get(feature, None)
           state_value = current_state[feature].iloc[0]
           if row_value == state_value:
               score += feature_weights[feature]
       return score


   filtered_df = pitcher_history_df.dropna(subset=['pitch_type']).copy()
   filtered_df['score'] = filtered_df.apply(score_row, axis=1)


   max_score = filtered_df['score'].max()
   top_rows = filtered_df[filtered_df['score'] == max_score]


   if len(top_rows) < k:
       remaining_rows_needed = k - len(top_rows)
       remaining_rows = filtered_df[filtered_df['score'] < max_score].nlargest(remaining_rows_needed, 'score')
       top_rows = pd.concat([top_rows, remaining_rows])


   confidence = 0


   for value in top_rows['score']:
       confidence += value
       conf_score = round(confidence / (len(top_rows)*11.628), 2) * 100


   pitch_type_counts = top_rows['pitch_type'].value_counts(normalize=True) * 100
   pitch_probs = {str(pitch): float(round(prob, 2)) for pitch, prob in pitch_type_counts.items()}


   result = {
       "balls": int(current_state['balls'][0]),
       "strikes": int(current_state['strikes'][0]),
       "outs": int(current_state['outs'][0]),
       "inning": int(current_state['inning'][0]),
       "away_score": int(current_state['away_score'][0]),
       "home_score": int(current_state['home_score'][0]),
       "last_pitch_type": str(current_state['last_pitch_type'][0]),
       "confidence_score": int(conf_score),
       "pitch_probabilities": pitch_probs
   }


   return result