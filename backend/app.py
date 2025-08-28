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
    df['RentalStartDate'] = pd.to_datetime(df['RentalStartDate'])
    df['ExpectedReturnDate'] = pd.to_datetime(df['ExpectedReturnDate'])
except FileNotFoundError:
    print("FATAL: rental_data.csv not found. The app cannot run.")
    df = pd.DataFrame()

# --- Machine Learning Models ---
# Anomaly Detection Model
# Contamination is the expected proportion of outliers in the data
anomaly_model = IsolationForest(contamination=0.05, random_state=42)
if not df.empty:
    telemetry_features = ['EngineHours', 'FuelLevel', 'EngineLoad']
    anomaly_model.fit(df[telemetry_features])
    # Predict anomalies (-1 for anomalies, 1 for inliers)
    df['IsAnomalous'] = anomaly_model.predict(df[telemetry_features])

# Predictive Availability Model
availability_model = LinearRegression()
if not df.empty and 'ActualReturnDate' in df.columns:
    # Calculate actual rental duration for training
    df_train = df.dropna(subset=['ActualReturnDate']).copy()
    df_train['ActualReturnDate'] = pd.to_datetime(df_train['ActualReturnDate'])
    df_train['ActualDuration'] = (df_train['ActualReturnDate'] - df_train['RentalStartDate']).dt.days
    
    # Simple model: predict duration based on engine hours
    X_train = df_train[['EngineHours']]
    y_train = df_train['ActualDuration']
    if len(X_train) > 0:
        availability_model.fit(X_train, y_train)

# --- Helper Functions ---
def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance between two points on Earth."""
    R = 6371  # Radius of Earth in kilometers
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat / 2) * math.sin(dLat / 2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2) * math.sin(dLon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c # distance in km

def generate_alerts(vehicle):
    """Generate alerts based on vehicle status and location."""
    alerts = []
    # 1. Geofence Alert
    dist_from_site = haversine(vehicle['Latitude'], vehicle['Longitude'], vehicle['JobSiteLat'], vehicle['JobSiteLon'])
    if dist_from_site > vehicle['JobSiteRadius']:
        alerts.append({
            "type": "Geofence",
            "message": f"Vehicle is {dist_from_site:.2f} km away from designated job site.",
            "level": "critical"
        })
    # 2. Anomaly Alert
    if vehicle['IsAnomalous'] == -1:
        alerts.append({
            "type": "Telemetry",
            "message": "Anomalous sensor readings detected. Recommend inspection.",
            "level": "warning"
        })
    # 3. Fuel Alert
    if vehicle['FuelLevel'] < 15:
        alerts.append({
            "type": "Fuel",
            "message": f"Low fuel warning: {vehicle['FuelLevel']}% remaining.",
            "level": "warning"
        })
    return alerts

# --- API Endpoints ---
@app.route('/api/summary', methods=['GET'])
def get_summary():
    """Endpoint for the main dashboard view."""
    if df.empty: return jsonify({"error": "Dataset not loaded"}), 500
    
    summary = df.groupby('Type')['Status'].value_counts().unstack(fill_value=0)
    summary['Total'] = summary.sum(axis=1)
    return jsonify(summary.to_dict(orient='index'))

@app.route('/api/equipment/type/<type_name>', methods=['GET'])
def get_equipment_by_type(type_name):
    """Endpoint for the category detail view."""
    if df.empty: return jsonify({"error": "Dataset not loaded"}), 500
    
    data = df[df['Type'] == type_name].copy()
    # Format dates for JSON compatibility
    data['RentalStartDate'] = data['RentalStartDate'].dt.strftime('%Y-%m-%d')
    data['ExpectedReturnDate'] = data['ExpectedReturnDate'].dt.strftime('%Y-%m-%d')
    return jsonify(data.to_dict(orient='records'))

@app.route('/api/equipment/id/<equipment_id>', methods=['GET'])
def get_equipment_by_id(equipment_id):
    """Endpoint for the specific vehicle detail view."""
    if df.empty: return jsonify({"error": "Dataset not loaded"}), 500
    
    vehicle_data = df[df['EquipmentID'] == equipment_id]
    if vehicle_data.empty:
        return jsonify({"error": "Vehicle not found"}), 404
        
    vehicle = vehicle_data.iloc[0].to_dict()
    vehicle['alerts'] = generate_alerts(vehicle)
    
    # Convert numpy types to native Python types for JSON serialization
    for key, value in vehicle.items():
        if isinstance(value, np.generic):
            vehicle[key] = value.item()
            
    # Convert timestamp to string
    vehicle['RentalStartDate'] = vehicle['RentalStartDate'].strftime('%Y-%m-%d')
    vehicle['ExpectedReturnDate'] = vehicle['ExpectedReturnDate'].strftime('%Y-%m-%d')
    
    return jsonify(vehicle)

@app.route('/api/predict-availability', methods=['POST'])
def predict_availability():
    """Endpoint to predict if a machine will be free by a future date."""
    if df.empty: return jsonify({"error": "Dataset not loaded"}), 500
    
    data = request.json
    equipment_id = data.get('equipmentId')
    future_date_str = data.get('futureDate')
    
    vehicle = df[df['EquipmentID'] == equipment_id].iloc[0]
    future_date = datetime.strptime(future_date_str, '%Y-%m-%d')

    if vehicle['Status'] == 'Available':
        return jsonify({"available": True, "predictedReturnDate": "Now"})

    # Predict duration using the model
    engine_hours_at_rental = vehicle[['EngineHours']]
    predicted_duration_days = availability_model.predict(engine_hours_at_rental)[0]
    
    predicted_return_date = vehicle['RentalStartDate'] + timedelta(days=int(predicted_duration_days))

    return jsonify({
        "available": future_date > predicted_return_date,
        "predictedReturnDate": predicted_return_date.strftime('%Y-%m-%d')
    })

# --- Main Execution ---
if __name__ == '__main__':
    app.run(debug=True)
