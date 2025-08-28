import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
import numpy as np
import math
import traceback

# --- App Initialization ---
app = Flask(__name__)
CORS(app)

# --- Data Loading and Preparation ---
try:
    df = pd.read_csv('rental_data.csv')
    # Convert date columns, coercing errors to NaT (Not a Time)
    df['RentalStartDate'] = pd.to_datetime(df['RentalStartDate'], errors='coerce')
    df['ExpectedReturnDate'] = pd.to_datetime(df['ExpectedReturnDate'], errors='coerce')
    print("CSV data loaded successfully.")
except FileNotFoundError:
    print("FATAL: rental_data.csv not found. The app cannot run.")
    df = pd.DataFrame()

# --- Machine Learning Models ---
anomaly_model = None
availability_model = None

if not df.empty:
    try:
        # Anomaly Detection Model
        anomaly_model = IsolationForest(contamination=0.05, random_state=42)
        telemetry_features = ['EngineHours', 'FuelLevel', 'EngineLoad']
        
        # More robust data cleaning for ML models
        for col in telemetry_features:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            if df[col].isnull().any():
                median_val = df[col].median()
                df[col].fillna(median_val, inplace=True)
        
        anomaly_model.fit(df[telemetry_features])
        df['IsAnomalous'] = anomaly_model.predict(df[telemetry_features])
        print("Anomaly detection model trained successfully.")

        # Predictive Availability Model
        availability_model = LinearRegression()
        if 'ActualReturnDate' in df.columns:
            df_train = df.dropna(subset=['ActualReturnDate', 'RentalStartDate']).copy()
            df_train['ActualReturnDate'] = pd.to_datetime(df_train['ActualReturnDate'], errors='coerce')
            df_train = df_train.dropna(subset=['ActualReturnDate', 'RentalStartDate'])

            if not df_train.empty:
                df_train['ActualDuration'] = (df_train['ActualReturnDate'] - df_train['RentalStartDate']).dt.days
                
                # Ensure there are no negative durations
                df_train = df_train[df_train['ActualDuration'] >= 0]

                X_train = df_train[['EngineHours']]
                y_train = df_train['ActualDuration']
                
                if not y_train.empty:
                    availability_model.fit(X_train, y_train)
                    print("Predictive availability model trained successfully.")
                else:
                    availability_model = None
                    print("Warning: No valid data to train availability model.")
            else:
                availability_model = None
                print("Warning: No complete historical data for training availability model.")
        else:
            availability_model = None
            print("Warning: 'ActualReturnDate' column not found. Cannot train availability model.")
    except Exception as e:
        print(f"Error during model training: {e}")
        traceback.print_exc()


# --- Helper Functions ---
def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance between two points on Earth."""
    R = 6371
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def generate_alerts(vehicle):
    """Generate alerts based on vehicle status and location."""
    alerts = []
    try:
        if pd.notna(vehicle.get('Latitude')) and pd.notna(vehicle.get('JobSiteLat')):
            dist_from_site = haversine(vehicle['Latitude'], vehicle['Longitude'], vehicle['JobSiteLat'], vehicle['JobSiteLon'])
            if dist_from_site > vehicle.get('JobSiteRadius', 1.0): # Default radius 1km
                alerts.append({"type": "Geofence", "message": f"Vehicle is {dist_from_site:.2f} km away from job site.", "level": "critical"})
        if vehicle.get('IsAnomalous') == -1:
            alerts.append({"type": "Telemetry", "message": "Anomalous sensor readings detected.", "level": "warning"})
        if pd.notna(vehicle.get('FuelLevel')) and vehicle['FuelLevel'] < 15:
            alerts.append({"type": "Fuel", "message": f"Low fuel: {vehicle['FuelLevel']}% remaining.", "level": "warning"})
    except Exception as e:
        print(f"Error generating alerts for {vehicle.get('EquipmentID')}: {e}")
    return alerts

# --- API Endpoints ---
@app.route('/api/summary', methods=['GET'])
def get_summary():
    if df.empty: return jsonify({"error": "Dataset not loaded"}), 500
    try:
        # FIX: The previous method was creating a structure that was difficult for the frontend to parse.
        # This revised method creates a clean list of objects, which is a standard and easy-to-use format.
        summary_df = df.groupby('Type')['Status'].value_counts().unstack(fill_value=0)
        summary_df['Total'] = summary_df.sum(axis=1)
        
        # Convert DataFrame to a list of dictionaries
        summary_list = []
        for index, row in summary_df.iterrows():
            summary_item = {
                'category': index,
                'statuses': row.to_dict()
            }
            summary_list.append(summary_item)
            
        return jsonify(summary_list)
    except Exception as e:
        print(f"Error in /api/summary: {e}")
        traceback.print_exc()
        return jsonify({"error": "Could not generate summary"}), 500

@app.route('/api/equipment/type/<type_name>', methods=['GET'])
def get_equipment_by_type(type_name):
    if df.empty: return jsonify({"error": "Dataset not loaded"}), 500
    try:
        data = df[df['Type'] == type_name].copy()
        data['RentalStartDate'] = data['RentalStartDate'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else None)
        data['ExpectedReturnDate'] = data['ExpectedReturnDate'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else None)
        return jsonify(data.to_dict(orient='records'))
    except Exception as e:
        print(f"Error in /api/equipment/type/{type_name}: {e}")
        return jsonify({"error": f"Could not retrieve data for {type_name}"}), 500

@app.route('/api/equipment/id/<equipment_id>', methods=['GET'])
def get_equipment_by_id(equipment_id):
    if df.empty: return jsonify({"error": "Dataset not loaded"}), 500
    try:
        vehicle_data = df[df['EquipmentID'] == equipment_id]
        if vehicle_data.empty:
            return jsonify({"error": "Vehicle not found"}), 404
            
        vehicle = vehicle_data.iloc[0].to_dict()
        vehicle['alerts'] = generate_alerts(vehicle)
        
        # Clean up data for JSON serialization
        for key, value in vehicle.items():
            if isinstance(value, np.generic):
                vehicle[key] = value.item()
            if pd.isna(value):
                vehicle[key] = None
        
        if vehicle.get('RentalStartDate'):
            vehicle['RentalStartDate'] = vehicle['RentalStartDate'].strftime('%Y-%m-%d')
        if vehicle.get('ExpectedReturnDate'):
            vehicle['ExpectedReturnDate'] = vehicle['ExpectedReturnDate'].strftime('%Y-%m-%d')
            
        return jsonify(vehicle)
    except Exception as e:
        print(f"Error in /api/equipment/id/{equipment_id}: {e}")
        return jsonify({"error": "Could not retrieve vehicle details"}), 500

@app.route('/api/predict-availability', methods=['POST'])
def predict_availability():
    if df.empty or availability_model is None:
        return jsonify({"error": "Prediction model is not available."}), 503
    try:
        data = request.json
        equipment_id = data.get('equipmentId')
        future_date_str = data.get('futureDate')
        
        vehicle_series = df[df['EquipmentID'] == equipment_id].iloc[0]
        future_date = datetime.strptime(future_date_str, '%Y-%m-%d')

        if vehicle_series['Status'] == 'Available':
            return jsonify({"available": True, "predictedReturnDate": "Now"})

        engine_hours_at_rental = vehicle_series[['EngineHours']]
        predicted_duration_days = availability_model.predict(engine_hours_at_rental)[0]
        
        rental_start_date = pd.to_datetime(vehicle_series['RentalStartDate'])
        if pd.isna(rental_start_date):
            return jsonify({"error": "Missing rental start date for prediction."}), 400

        predicted_return_date = rental_start_date + timedelta(days=int(predicted_duration_days))

        return jsonify({
            "available": future_date > predicted_return_date,
            "predictedReturnDate": predicted_return_date.strftime('%Y-%m-%d')
        })
    except Exception as e:
        print(f"Error in /api/predict-availability: {e}")
        traceback.print_exc()
        return jsonify({"error": "Could not make a prediction."}), 500

# --- Main Execution ---
if __name__ == '__main__':
    app.run(debug=True)
