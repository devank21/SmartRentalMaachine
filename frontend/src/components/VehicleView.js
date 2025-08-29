import React, { useState, useEffect } from "react";
import axios from "axios";
import { MapContainer, TileLayer, Marker, Popup, Circle } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import "./VehicleView.css"; // New CSS file for this component

// Leaflet Icon Fix
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require("leaflet/dist/images/marker-icon-2x.png"),
  iconUrl: require("leaflet/dist/images/marker-icon.png"),
  shadowUrl: require("leaflet/dist/images/marker-shadow.png"),
});

const API_BASE_URL = "http://localhost:5000/api";

const VehicleView = ({ equipmentId, category, navigateTo }) => {
  const [vehicle, setVehicle] = useState(null);
  const [error, setError] = useState("");
  const [prediction, setPrediction] = useState(null);
  const [date, setDate] = useState("");
  const [pricePrediction, setPricePrediction] = useState(null);
  const [duration, setDuration] = useState(90);
  const [behaviorAnalysis, setBehaviorAnalysis] = useState(null); // State for new feature
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const fetchVehicleData = () => {
    axios
      .get(`${API_BASE_URL}/equipment/id/${equipmentId}`)
      .then((res) => setVehicle(res.data))
      .catch((err) => setError("Could not load vehicle details."));
  };

  useEffect(() => {
    fetchVehicleData();
  }, [equipmentId]);

  const handleBehaviorAnalysis = () => {
    setIsAnalyzing(true);
    setBehaviorAnalysis(null);
    axios
      .get(`${API_BASE_URL}/analyze-behavior/${equipmentId}`)
      .then((res) => setBehaviorAnalysis(res.data))
      .catch((err) =>
        setBehaviorAnalysis({
          error: err.response?.data?.error || "Analysis failed.",
        })
      )
      .finally(() => setIsAnalyzing(false));
  };

  // Other handlers (unchanged)
  const handleAvailabilityPrediction = () => {
    if (!date) return;
    axios
      .post(`${API_BASE_URL}/predict-availability`, {
        equipmentId,
        futureDate: date,
      })
      .then((res) => setPrediction(res.data))
      .catch((err) =>
        setPrediction({
          error: err.response?.data?.error || "Could not get prediction.",
        })
      );
  };
  const handlePricePrediction = () => {
    axios
      .post(`${API_BASE_URL}/predict-price`, {
        engineHours: vehicle.EngineHours,
        durationDays: duration,
      })
      .then((res) => setPricePrediction(res.data))
      .catch((err) =>
        setPricePrediction({
          error: err.response?.data?.error || "Could not get price.",
        })
      );
  };
  const handleReturnVehicle = () => {
    axios
      .post(`${API_BASE_URL}/return-vehicle`, { equipmentId })
      .then(() => fetchVehicleData());
  };

  // Render helpers (unchanged)
  const renderPredictionResult = (pred) => {
    if (!pred) return null;
    if (pred.error)
      return <div className="prediction-result error">{pred.error}</div>;
    if (pred.available)
      return (
        <div className="prediction-result available">
          Predicted AVAILABLE on {date}.
        </div>
      );
    return (
      <div className="prediction-result in-use">
        Predicted IN-USE. Expected return: {pred.predictedReturnDate}.
      </div>
    );
  };
  const renderPriceResult = (price) => {
    if (!price) return null;
    if (price.error)
      return <div className="prediction-result error">{price.error}</div>;
    return (
      <div className="prediction-result success">
        Estimated Price: ${price.predictedPrice.toLocaleString()}
      </div>
    );
  };

  if (error) return <div className="error-message">{error}</div>;
  if (!vehicle) return <div className="loading">Loading vehicle data...</div>;

  return (
    <div className="view-container">
      <div className="vehicle-header">
        <h2>Vehicle Details: {vehicle.EquipmentID}</h2>
        {vehicle.Status === "In-Use" && (
          <button className="return-button" onClick={handleReturnVehicle}>
            Mark as Returned
          </button>
        )}
      </div>

      <div className="vehicle-grid">
        {/* Map, Telemetry, and Alerts (grid items 1, 2, 3) */}
        <div className="vehicle-card map-card">
          <h3>Live Location & Geofence</h3>
          <MapContainer
            center={[vehicle.Latitude, vehicle.Longitude]}
            zoom={14}
            style={{ height: "50%", width: "50%" }}
          >
            <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
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
            <span>Status</span>
            <strong>{vehicle.Status}</strong>
          </div>
          <div className="telemetry-item">
            <span>Customer</span>
            <strong>{vehicle.Customer || "N/A"}</strong>
          </div>
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
          {vehicle.alerts?.length > 0 ? (
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

        {/* Behavioral Anomaly Detection Card (grid item 4) */}
        <div className="vehicle-card prediction-card full-width">
          <h3>Behavioral Anomaly Detection (LSTM Autoencoder)</h3>
          <p>
            Analyze the last 30 operational data points to detect unusual
            patterns in engine behavior.
          </p>
          <div className="prediction-controls">
            <button onClick={handleBehaviorAnalysis} disabled={isAnalyzing}>
              {isAnalyzing ? "Analyzing..." : "Run Behavioral Analysis"}
            </button>
          </div>
          {behaviorAnalysis && (
            <div className="behavior-analysis-result">
              {behaviorAnalysis.error ? (
                <p className="error-message">{behaviorAnalysis.error}</p>
              ) : (
                <>
                  <div
                    className={`analysis-summary ${
                      behaviorAnalysis.is_anomaly ? "anomaly" : "normal"
                    }`}
                  >
                    Status:{" "}
                    {behaviorAnalysis.is_anomaly
                      ? "Anomaly Detected"
                      : "Normal Operation"}
                  </div>
                  <p>
                    <strong>Reconstruction Error:</strong>{" "}
                    {behaviorAnalysis.reconstruction_error.toFixed(4)}
                  </p>
                  <p>
                    <strong>Anomaly Threshold:</strong>{" "}
                    {behaviorAnalysis.threshold.toFixed(4)}
                  </p>
                  <div className="chart-container-small">
                    <ResponsiveContainer width="100%" height={200}>
                      <LineChart data={behaviorAnalysis.sequence_data}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="Timestamp" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Line
                          type="monotone"
                          dataKey="EngineLoad"
                          name="Engine Load (%)"
                          stroke="#8884d8"
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {/* Availability and Pricing (grid items 5, 6) */}
        <div className="vehicle-card prediction-card">
          <h3>Predict Availability</h3>
          <div className="prediction-controls">
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
            <button onClick={handleAvailabilityPrediction}>Check</button>
          </div>
          {renderPredictionResult(prediction)}
        </div>
        <div className="vehicle-card prediction-card">
          <h3>Dynamic Price Estimation</h3>
          <div className="prediction-controls">
            <label>Duration (days):</label>
            <input
              type="number"
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
            />
            <button onClick={handlePricePrediction}>Predict Price</button>
          </div>
          {renderPriceResult(pricePrediction)}
        </div>
      </div>
    </div>
  );
};

export default VehicleView;
