import pandas as pd
from flask import Flask, jsonify
from flask_cors import CORS
from statsmodels.tsa.arima.model import ARIMA
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

# Initialize Flask App and CORS
app = Flask(__name__)
CORS(app)  # This enables Cross-Origin Resource Sharing

# --- Data Loading and Preparation ---
try:
    # Load the dataset
    df = pd.read_csv('rental_data.csv')
    # Convert CheckInDate to datetime objects for time-series analysis
    df['CheckInDate'] = pd.to_datetime(df['CheckInDate'])
except FileNotFoundError:
    print("Error: rental_data.csv not found. Make sure the file is in the backend directory.")
    df = pd.DataFrame() # Create an empty dataframe to avoid crashing

# --- API Endpoints ---

@app.route('/api/equipment', methods=['GET'])
def get_equipment():
    """
    API endpoint to get the latest status of all equipment.
    This simulates fetching real-time data from a database.
    """
    if df.empty:
        return jsonify({"error": "Dataset not loaded"}), 500
        
    # For this simulation, we'll return the entire dataset as if it's the current state.
    # In a real-world scenario, you would query a database for the most recent entry for each EquipmentID.
    equipment_list = df.to_dict(orient='records')
    return jsonify(equipment_list)

@app.route('/api/forecast', methods=['GET'])
def get_forecast():
    """
    API endpoint to generate and return a 30-day demand forecast.
    """
    if df.empty:
        return jsonify({"error": "Dataset not loaded"}), 500

    try:
        # --- Time Series Forecasting Logic ---
        # 1. Aggregate data to get daily rental counts
        daily_counts = df.set_index('CheckInDate').resample('D').size()
        
        # Ensure we have enough data to train
        if len(daily_counts) < 60:
             return jsonify({"error": "Not enough historical data to generate a forecast."}), 400

        # 2. Train the ARIMA model
        # The (p,d,q) order is a common starting point for seasonal data.
        # p: Autoregressive order
        # d: Differencing order
        # q: Moving average order
        model = ARIMA(daily_counts, order=(7, 1, 1))
        model_fit = model.fit()

        # 3. Generate a 30-day forecast
        forecast_result = model_fit.get_forecast(steps=30)
        
        # Extract forecast values and confidence intervals
        forecast_values = forecast_result.predicted_mean
        confidence_intervals = forecast_result.conf_int()

        # 4. Format the data for the frontend chart
        response_data = {
            "historical": {
                "dates": daily_counts.index.strftime('%Y-%m-%d').tolist(),
                "values": daily_counts.values.tolist()
            },
            "forecast": {
                "dates": forecast_values.index.strftime('%Y-%m-%d').tolist(),
                "values": forecast_values.values.tolist(),
                "lower_bound": confidence_intervals.iloc[:, 0].values.tolist(),
                "upper_bound": confidence_intervals.iloc[:, 1].values.tolist()
            }
        }
        return jsonify(response_data)
        
    except Exception as e:
        # Catch any errors during model training or forecasting
        print(f"Error during forecasting: {e}")
        return jsonify({"error": "An error occurred while generating the forecast."}), 500

# --- Main execution block ---
if __name__ == '__main__':
    # Runs the Flask app on localhost, port 5000
    # debug=True allows for auto-reloading when code changes are saved
    app.run(debug=True)
