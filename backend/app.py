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
    # DEFINITIVE FIX: Read empty strings as NaN and then replace all NaN with None (null)
    df = pd.read_csv('rental_data.csv', na_values=['N/A', 'NaN', ''])
    df = df.replace({np.nan: None})

    df['RentalStartDate'] = pd.to_datetime(df['RentalStartDate'], errors='coerce')
    df['ExpectedReturnDate'] = pd.to_datetime(df['ExpectedReturnDate'], errors='coerce')
    print("CSV data loaded and cleaned successfully.")
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
        for col in telemetry_features:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            # Use the overall median for filling missing telemetry data
            df[col].fillna(df[col].median(), inplace=True)
            
        anomaly_model.fit(df[telemetry_features])
        df['IsAnomalous'] = anomaly_model.predict(df[telemetry_features])
        print("Anomaly detection model trained successfully.")

        # Predictive Availability Model
        availability_model = LinearRegression()
        if 'ActualReturnDate' in df.columns:
            df_train = df.dropna(subset=['ActualReturnDate', 'RentalStartDate', 'EngineHours']).copy()
            df_train['ActualReturnDate'] = pd.to_datetime(df_train['ActualReturnDate'], errors='coerce')
            if not df_train.empty:
                df_train['ActualDuration'] = (df_train['ActualReturnDate'] - df_train['RentalStartDate']).dt.days
                df_train = df_train[df_train['ActualDuration'] >= 0]
                if not df_train.empty:
                    X_train = df_train[['EngineHours']]
                    y_train = df_train['ActualDuration']
                    availability_model.fit(X_train, y_train)
                    print("Predictive availability model trained successfully.")
                else: availability_model = None
            else: availability_model = None
        else: availability_model = None
    except Exception as e:
        print(f"Error during model training: {e}")
        traceback.print_exc()

# --- Helper Functions ---
def haversine(lat1, lon1, lat2, lon2):
    if any(v is None for v in [lat1, lon1, lat2, lon2]): return None
    R = 6371
    dLat, dLon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dLat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def generate_alerts(vehicle):
    alerts = []
    dist = haversine(vehicle.get('Latitude'), vehicle.get('Longitude'), vehicle.get('JobSiteLat'), vehicle.get('JobSiteLon'))
    if dist is not None and vehicle.get('JobSiteRadius') is not None and dist > vehicle['JobSiteRadius']:
        alerts.append({"type": "Geofence", "message": f"Vehicle is {dist:.2f} km from job site.", "level": "critical"})
    if vehicle.get('IsAnomalous') == -1:
        alerts.append({"type": "Telemetry", "message": "Anomalous sensor readings.", "level": "warning"})
    if vehicle.get('FuelLevel') is not None and vehicle['FuelLevel'] < 15:
        alerts.append({"type": "Fuel", "message": f"Low fuel: {vehicle['FuelLevel']}%", "level": "warning"})
    return alerts

# --- API Endpoints ---
@app.route('/api/summary', methods=['GET'])
def get_summary():
    if df.empty: return jsonify({"error": "Dataset not loaded"}), 500
    try:
        summary_df = df.groupby('Type')['Status'].value_counts().unstack(fill_value=0)
        if 'Total' not in summary_df: summary_df['Total'] = summary_df.sum(axis=1)
        summary_list = [{'category': index, 'statuses': row.to_dict()} for index, row in summary_df.iterrows()]
        return jsonify({'data': summary_list})
    except Exception as e:
        return jsonify({"error": "Could not generate summary"}), 500

@app.route('/api/equipment/type/<type_name>', methods=['GET'])
def get_equipment_by_type(type_name):
    if df.empty: return jsonify({"error": "Dataset not loaded"}), 500
    try:
        data = df[df['Type'] == type_name].copy()
        data['RentalStartDate'] = data['RentalStartDate'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else None)
        data['ExpectedReturnDate'] = data['ExpectedReturnDate'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else None)
        # DEFINITIVE FIX: Convert dataframe to dict, which handles the None conversion correctly
        clean_data = data.to_dict(orient='records')
        return jsonify({'data': clean_data})
    except Exception as e:
        return jsonify({"error": f"Could not retrieve data for {type_name}"}), 500

@app.route('/api/equipment/id/<equipment_id>', methods=['GET'])
def get_equipment_by_id(equipment_id):
    if df.empty: return jsonify({"error": "Dataset not loaded"}), 500
    try:
        vehicle_data = df[df['EquipmentID'] == equipment_id]
        if vehicle_data.empty: return jsonify({"error": "Vehicle not found"}), 404
        vehicle = vehicle_data.iloc[0].to_dict() # .to_dict() is safe now
        vehicle['alerts'] = generate_alerts(vehicle)
        if vehicle.get('RentalStartDate'): vehicle['RentalStartDate'] = vehicle['RentalStartDate'].strftime('%Y-%m-%d')
        if vehicle.get('ExpectedReturnDate'): vehicle['ExpectedReturnDate'] = vehicle['ExpectedReturnDate'].strftime('%Y-%m-%d')
        return jsonify(vehicle)
    except Exception as e:
        return jsonify({"error": "Could not retrieve vehicle details"}), 500

@app.route('/api/predict-availability', methods=['POST'])
def predict_availability():
    if df.empty or availability_model is None:
        return jsonify({"error": "Prediction model is not available."}), 503
    try:
        data = request.json
        vehicle = df[df['EquipmentID'] == data.get('equipmentId')].iloc[0]
        future_date = datetime.strptime(data.get('futureDate'), '%Y-%m-%d')
        if vehicle['Status'] == 'Available':
            return jsonify({"available": True, "predictedReturnDate": "Now"})
        if pd.isna(vehicle['RentalStartDate']):
            return jsonify({"error": "Cannot predict: Missing rental start date."}), 400
        engine_hours = vehicle[['EngineHours']]
        duration_days = availability_model.predict(engine_hours)[0]
        predicted_return = vehicle['RentalStartDate'] + timedelta(days=int(duration_days))
        return jsonify({
            "available": future_date > predicted_return,
            "predictedReturnDate": predicted_return.strftime('%Y-%m-%d')
        })
    except Exception as e:
        return jsonify({"error": "Could not make a prediction."}), 500

# --- Main Execution ---
if __name__ == '__main__':
    app.run(debug=True)