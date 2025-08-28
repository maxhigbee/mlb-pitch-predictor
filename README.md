## About

This is a Flask web application that predicts the next pitch type in a live MLB game by analyzing real-time game data like batter handedness, count, inning, and more.

The app provides a list of live games and real-time next pitch predictions based on game context and pitcher history and delivers it in a clean interface. Using a KNN model, the pitcher's most similar historical game situations are identified and a probability breakdown of the next pitch type is displayed.

## Key Functions:

`get_date()` – Returns today’s date in Eastern Time for schedule and historical data queries.

`live_games()` – Flask route /live_games returning all in-progress MLB games in JSON format.

`predict_pitch_once(game_id)` – Predicts the next pitch for a given game using historical pitcher data and current game context.

`get_pitcher_data(pitcher_id, start_date, end_date)` – Retrieves historical pitch-by-pitch data for a pitcher.

`get_game_data(game_id)` – Retrieves the live game state from MLB Stats API.

`/predict_pitch` – Flask route returning JSON predictions for a specific game ID.

`/` – Serves the front-end interface (index.html) for users to interact with live games and pitch predictions.

## Credit

Live pitch-by-pitch data was pulled from the MLB API using the following endpoint:

https://statsapi.mlb.com/api/v1.1/game/{game_id}/feed/live/diffPatch

The [pybaseball](https://github.com/jldbc/pybaseball) package was also used for fetching historical pitcher data.
