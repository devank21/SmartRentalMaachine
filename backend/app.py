import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
import numpy as np
import math

# --- App Initialization ---
app = Flask(__name__)
CORS(app)

# --- Data Loading and Preparation ---
try:
    df = pd.read_csv('rental_data.csv')
    # Convert date columns, coercing errors to NaT (Not a Time)
    df['RentalStartDate'] = pd.to_datetime(df['RentalStartDate'], errors='coerce')
    df['ExpectedReturnDate'] = pd.to_datetime(df['ExpectedReturnDate'], errors='coerce')
except FileNotFoundError:
    print("FATAL: rental_data.csv not found. The app cannot run.")
    df = pd.DataFrame()

# --- Machine Learning Models ---
# Anomaly Detection Model
anomaly_model = IsolationForest(contamination=0.05, random_state=42)
if not df.empty:
    # FIX: Ensure all telemetry features are numeric and handle potential missing values
    # by filling them with the median. This prevents the model from failing on non-numeric data.
    telemetry_features = ['EngineHours', 'FuelLevel', 'EngineLoad']
    for col in telemetry_features:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        df[col].fillna(df[col].median(), inplace=True)
        
    anomaly_model.fit(df[telemetry_features])
    df['IsAnomalous'] = anomaly_model.predict(df[telemetry_features])

# Predictive Availability Model
availability_model = LinearRegression()
if not df.empty and 'ActualReturnDate' in df.columns:
    df_train = df.dropna(subset=['ActualReturnDate', 'RentalStartDate']).copy()
    df_train['ActualReturnDate'] = pd.to_datetime(df_train['ActualReturnDate'], errors='coerce')
    
    # FIX: Filter out rows where date conversion failed
    df_train = df_train.dropna(subset=['ActualReturnDate', 'RentalStartDate'])

    df_train['ActualDuration'] = (df_train['ActualReturnDate'] - df_train['RentalStartDate']).dt.days
    
    X_train = df_train[['EngineHours']]
    y_train = df_train['ActualDuration']
    if len(X_train) > 0 and len(y_train) > 0 and not y_train.isnull().all():
        availability_model.fit(X_train, y_train)

# --- Helper Functions ---
def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance between two points on Earth."""
    R = 6371
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat / 2) * math.sin(dLat / 2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2) * math.sin(dLon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def generate_alerts(vehicle):
    """Generate alerts based on vehicle status and location."""
    alerts = []
    if pd.notna(vehicle['Latitude']) and pd.notna(vehicle['Longitude']) and pd.notna(vehicle['JobSiteLat']) and pd.notna(vehicle['JobSiteLon']):
        dist_from_site = haversine(vehicle['Latitude'], vehicle['Longitude'], vehicle['JobSiteLat'], vehicle['JobSiteLon'])
        if dist_from_site > vehicle['JobSiteRadius']:
            alerts.append({"type": "Geofence", "message": f"Vehicle is {dist_from_site:.2f} km away from designated job site.", "level": "critical"})
    if vehicle.get('IsAnomalous') == -1:
        alerts.append({"type": "Telemetry", "message": "Anomalous sensor readings detected. Recommend inspection.", "level": "warning"})
    if pd.notna(vehicle['FuelLevel']) and vehicle['FuelLevel'] < 15:
        alerts.append({"type": "Fuel", "message": f"Low fuel warning: {vehicle['FuelLevel']}% remaining.", "level": "warning"})
    return alerts

# --- API Endpoints ---
@app.route('/api/summary', methods=['GET'])
def get_summary():
    if df.empty: return jsonify({"error": "Dataset not loaded"}), 500
    summary = df.groupby('Type')['Status'].value_counts().unstack(fill_value=0).to_dict(orient='index')
    # Add 'Total' to each summary object
    for cat, statuses in summary.items():
        summary[cat]['Total'] = sum(statuses.values())
    return jsonify(summary)

@app.route('/api/equipment/type/<type_name>', methods=['GET'])
def get_equipment_by_type(type_name):
    if df.empty: return jsonify({"error": "Dataset not loaded"}), 500
    data = df[df['Type'] == type_name].copy()
    
    data['RentalStartDate'] = data['RentalStartDate'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else None)
    data['ExpectedReturnDate'] = data['ExpectedReturnDate'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else None)
    
    return jsonify(data.to_dict(orient='records'))

@app.route('/api/equipment/id/<equipment_id>', methods=['GET'])
def get_equipment_by_id(equipment_id):
    if df.empty: return jsonify({"error": "Dataset not loaded"}), 500
    vehicle_data = df[df['EquipmentID'] == equipment_id]
    if vehicle_data.empty:
        return jsonify({"error": "Vehicle not found"}), 404
        
    vehicle = vehicle_data.iloc[0].to_dict()
    vehicle['alerts'] = generate_alerts(vehicle)
    
    for key, value in vehicle.items():
        if isinstance(value, np.generic):
            vehicle[key] = value.item()
            
    if pd.notna(vehicle.get('RentalStartDate')):
        vehicle['RentalStartDate'] = vehicle['RentalStartDate'].strftime('%Y-%m-%d')
    else:
        vehicle['RentalStartDate'] = None
    if pd.notna(vehicle.get('ExpectedReturnDate')):
        vehicle['ExpectedReturnDate'] = vehicle['ExpectedReturnDate'].strftime('%Y-%m-%d')
    else:
        vehicle['ExpectedReturnDate'] = None
        
    return jsonify(vehicle)

@app.route('/api/predict-availability', methods=['POST'])
def predict_availability():
    if df.empty: return jsonify({"error": "Dataset not loaded"}), 500
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

# --- Main Execution ---
if __name__ == '__main__':
    app.run(debug=True)
