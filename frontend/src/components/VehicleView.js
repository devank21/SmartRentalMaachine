import React, { useState, useEffect } from "react";
import axios from "axios";
import { MapContainer, TileLayer, Marker, Popup, Circle } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

// Leaflet Icon Fix
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require("leaflet/dist/images/marker-icon-2x.png"),
  iconUrl: require("leaflet/dist/images/marker-icon.png"),
  shadowUrl: require("leaflet/dist/images/marker-shadow.png"),
});

const API_BASE_URL = "http://127.0.0.1:5000/api";

const VehicleView = ({ equipmentId, category, navigateTo }) => {
  const [vehicle, setVehicle] = useState(null);
  const [error, setError] = useState("");
  const [prediction, setPrediction] = useState(null);
  const [date, setDate] = useState("");

  useEffect(() => {
    axios
      .get(`${API_BASE_URL}/equipment/id/${equipmentId}`)
      .then((res) => setVehicle(res.data))
      .catch((err) => {
        console.error(`Error fetching vehicle ${equipmentId}:`, err);
        setError("Could not load vehicle details.");
      });
  }, [equipmentId]);

  const handlePrediction = () => {
    if (!date) return;
    setPrediction(null); // Clear previous prediction
    axios
      .post(`${API_BASE_URL}/predict-availability`, {
        equipmentId,
        futureDate: date,
      })
      .then((res) => {
        // Set the new prediction from the successful response
        setPrediction(res.data);
      })
      .catch((err) => {
        // If there's an error, set the prediction state to show the error message
        console.error("Prediction error:", err);
        if (err.response && err.response.data && err.response.data.error) {
          setPrediction({ error: err.response.data.error });
        } else {
          setPrediction({ error: "Could not get a prediction." });
        }
      });
  };

  // Helper to render the prediction result
  const renderPredictionResult = () => {
    if (!prediction) return null;

    if (prediction.error) {
      return <div className="prediction-result error">{prediction.error}</div>;
    }

    if (prediction.available) {
      return (
        <div className="prediction-result available">
          Predicted to be AVAILABLE on {date}.
        </div>
      );
    } else {
      return (
        <div className="prediction-result in-use">
          Predicted to be IN-USE. Expected return:{" "}
          {prediction.predictedReturnDate}.
        </div>
      );
    }
  };

  if (error) return <div className="error-message">{error}</div>;
  if (!vehicle) return <div className="loading">Loading vehicle data...</div>;

  return (
    <div className="view-container">
      <button
        className="back-button"
        onClick={() => navigateTo("category", { category: vehicle.Type })}
      >
        &larr; Back to {vehicle.Type}
      </button>
      <h2>Vehicle Details: {vehicle.EquipmentID}</h2>

      <div className="vehicle-grid">
        <div className="vehicle-card map-card">
          <h3>Live Location & Geofence</h3>
          <MapContainer
            center={[vehicle.Latitude, vehicle.Longitude]}
            zoom={14}
            style={{ height: "100%", width: "100%" }}
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            />
            <Marker position={[vehicle.Latitude, vehicle.Longitude]}>
              <Popup>{vehicle.EquipmentID}</Popup>
            </Marker>
            {vehicle.JobSiteLat && vehicle.JobSiteLon && (
              <Circle
                center={[vehicle.JobSiteLat, vehicle.JobSiteLon]}
                radius={vehicle.JobSiteRadius * 1000}
                pathOptions={{ color: "green", fillColor: "green" }}
              />
            )}
          </MapContainer>
        </div>

        <div className="vehicle-card telemetry-card">
          <h3>Live Telemetry</h3>
          <div className="telemetry-item">
            <span>Fuel Level</span>
            <div className="progress-bar">
              <div style={{ width: `${vehicle.FuelLevel}%` }}>
                {vehicle.FuelLevel}%
              </div>
            </div>
          </div>
          <div className="telemetry-item">
            <span>Engine Hours</span>
            <strong>{vehicle.EngineHours} hrs</strong>
          </div>
          <div className="telemetry-item">
            <span>Engine Load</span>
            <div className="progress-bar">
              <div style={{ width: `${vehicle.EngineLoad}%` }}>
                {vehicle.EngineLoad}%
              </div>
            </div>
          </div>
        </div>

        <div className="vehicle-card alerts-card">
          <h3>System Alerts</h3>
          {vehicle.alerts && vehicle.alerts.length > 0 ? (
            <ul>
              {vehicle.alerts.map((alert, i) => (
                <li key={i} className={`alert-${alert.level}`}>
                  <strong>{alert.type}:</strong> {alert.message}
                </li>
              ))}
            </ul>
          ) : (
            <p>No active alerts.</p>
          )}
        </div>

        <div className="vehicle-card prediction-card">
          <h3>Predict Availability</h3>
          <p>Check if this machine will be free for a future date.</p>
          <div className="prediction-controls">
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
            <button onClick={handlePrediction}>Check</button>
          </div>
          {renderPredictionResult()}
        </div>
      </div>
    </div>
  );
};

export default VehicleView;
