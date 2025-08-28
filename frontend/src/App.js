import React, { useState, useEffect } from "react";
import axios from "axios";

/*
  =====================================================================================
  =====================================================================================
  ======                                                                         ======
  ======    STOP: A CRITICAL STEP IS REQUIRED TO FIX THE COMPILATION ERROR       ======
  ======                                                                         ======
  =====================================================================================
  =====================================================================================
  
  The "Could not resolve 'react-leaflet'" error means essential software packages
  are missing from your project. The code itself is correct, but it cannot find
  the libraries it needs to run.

  To fix this, you MUST install these packages from your terminal.

  --- FOLLOW THESE 5 STEPS EXACTLY ---

  1. Open your computer's terminal or command prompt.

  2. Navigate into your project's `frontend` folder.
     Example: cd path/to/your/SmartRentalSystem/frontend

  3. If the React server is running, stop it by pressing CTRL+C.

  4. Run this precise command. It will download and install everything needed.
     Copy and paste it to avoid typos:

     npm install axios leaflet react-leaflet

  5. After the installation is complete, restart the server:

     npm start

  This will permanently resolve the error. The application will not work
  until this command is run successfully.

  =====================================================================================
*/

import { MapContainer, TileLayer, Marker, Popup, Circle } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

// --- Leaflet Icon Fix ---
import iconUrl from "leaflet/dist/images/marker-icon.png";
import iconRetinaUrl from "leaflet/dist/images/marker-icon-2x.png";
import shadowUrl from "leaflet/dist/images/marker-shadow.png";

const DefaultIcon = L.icon({
  iconUrl,
  iconRetinaUrl,
  shadowUrl,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});
L.Marker.prototype.options.icon = DefaultIcon;

// --- API Configuration ---
const API_BASE_URL = "http://127.0.0.1:5000/api";

// --- Main App Component (Router) ---
function App() {
  const [view, setView] = useState({ name: "dashboard" });

  const navigateTo = (viewName, props = {}) => {
    setView({ name: viewName, ...props });
  };

  const renderView = () => {
    switch (view.name) {
      case "category":
        return (
          <CategoryDetailView
            category={view.category}
            navigateTo={navigateTo}
          />
        );
      case "vehicle":
        return (
          <VehicleDetailView
            equipmentId={view.equipmentId}
            navigateTo={navigateTo}
          />
        );
      default:
        return <DashboardView navigateTo={navigateTo} />;
    }
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="logo" onClick={() => navigateTo("dashboard")}>
          CAT
        </div>
        <h1>Smart Fleet Command Center</h1>
      </header>
      <main className="main-content">{renderView()}</main>
    </div>
  );
}

// --- Dashboard View ---
const DashboardView = ({ navigateTo }) => {
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    axios
      .get(`${API_BASE_URL}/summary`)
      .then((res) => setSummary(res.data))
      .catch((err) => {
        console.error(err);
        setError("Could not load dashboard summary. Is the backend running?");
      });
  }, []);

  if (error) return <div className="error-message">{error}</div>;
  if (!summary)
    return <div className="loading-message">Loading Dashboard...</div>;

  return (
    <div className="dashboard-grid">
      {Object.entries(summary).map(([category, statuses]) => (
        <div
          key={category}
          className="summary-card"
          onClick={() => navigateTo("category", { category })}
        >
          <h2>{category}</h2>
          <p className="total-count">{statuses.Total} Total Units</p>
          <div className="status-breakdown">
            <div className="status-item available">
              {statuses.Available || 0} <span>Available</span>
            </div>
            <div className="status-item in-use">
              {statuses["In-Use"] || 0} <span>In-Use</span>
            </div>
            <div className="status-item maintenance">
              {statuses.Maintenance || 0} <span>Maintenance</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

// --- Category Detail View ---
const CategoryDetailView = ({ category, navigateTo }) => {
  const [equipment, setEquipment] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    axios
      .get(`${API_BASE_URL}/equipment/type/${category}`)
      .then((res) => {
        if (Array.isArray(res.data)) {
          setEquipment(res.data);
        } else {
          console.error(
            "API did not return an array for equipment list:",
            res.data
          );
          setError("Received invalid data format from the server.");
        }
      })
      .catch((err) => {
        console.error(err);
        setError("Could not load equipment details.");
      });
  }, [category]);

  if (error) return <div className="error-message">{error}</div>;

  return (
    <div className="detail-view-container">
      <button className="back-button" onClick={() => navigateTo("dashboard")}>
        &larr; Back to Dashboard
      </button>
      <h2>{category} Fleet Status</h2>
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Status</th>
              <th>Rented By</th>
              <th>Expected Return</th>
            </tr>
          </thead>
          <tbody>
            {equipment.map((item) => (
              <tr
                key={item.EquipmentID}
                onClick={() =>
                  navigateTo("vehicle", { equipmentId: item.EquipmentID })
                }
              >
                <td className="id-cell">{item.EquipmentID}</td>
                <td>
                  <span
                    className={`status-badge status-${item.Status.toLowerCase().replace(
                      " ",
                      "-"
                    )}`}
                  >
                    {item.Status}
                  </span>
                </td>
                <td>{item.Customer || "N/A"}</td>
                <td>
                  {item.Status === "In-Use" ? item.ExpectedReturnDate : "N/A"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// --- Vehicle Detail View ---
const VehicleDetailView = ({ equipmentId, navigateTo }) => {
  const [vehicle, setVehicle] = useState(null);
  const [error, setError] = useState("");
  const [prediction, setPrediction] = useState(null);
  const [date, setDate] = useState("");

  useEffect(() => {
    axios
      .get(`${API_BASE_URL}/equipment/id/${equipmentId}`)
      .then((res) => setVehicle(res.data))
      .catch((err) => {
        console.error(err);
        setError("Could not load vehicle details.");
      });
  }, [equipmentId]);

  const handlePrediction = () => {
    if (!date) return;
    axios
      .post(`${API_BASE_URL}/predict-availability`, {
        equipmentId,
        futureDate: date,
      })
      .then((res) => setPrediction(res.data))
      .catch((err) => console.error(err));
  };

  if (error) return <div className="error-message">{error}</div>;
  if (!vehicle)
    return <div className="loading-message">Loading Vehicle Data...</div>;

  return (
    <div className="detail-view-container">
      <button
        className="back-button"
        onClick={() => navigateTo("category", { category: vehicle.Type })}
      >
        &larr; Back to {vehicle.Type}s
      </button>
      <h2>Vehicle Details: {vehicle.EquipmentID}</h2>
      <div className="vehicle-grid">
        <div className="vehicle-card map-card">
          <h3>Live Location & Geofence</h3>
          <MapContainer
            center={[vehicle.Latitude, vehicle.Longitude]}
            zoom={13}
            style={{ height: "100%", width: "100%" }}
          >
            <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" />
            <Marker position={[vehicle.Latitude, vehicle.Longitude]}>
              <Popup>{vehicle.EquipmentID}</Popup>
            </Marker>
            <Circle
              center={[vehicle.JobSiteLat, vehicle.JobSiteLon]}
              radius={vehicle.JobSiteRadius * 1000}
              color="yellow"
              fillOpacity={0.1}
            />
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
            <p>{vehicle.EngineHours} hrs</p>
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
          {vehicle.alerts.length > 0 ? (
            <ul>
              {vehicle.alerts.map((alert, i) => (
                <li key={i} className={`alert-${alert.level}`}>
                  {alert.message}
                </li>
              ))}
            </ul>
          ) : (
            <p>No active alerts.</p>
          )}
        </div>
        <div className="vehicle-card prediction-card">
          <h3>Predict Availability</h3>
          <p>Check if this machine will be free for a future rental.</p>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
          <button onClick={handlePrediction}>Check</button>
          {prediction && (
            <div
              className={`prediction-result ${
                prediction.available ? "available" : "in-use"
              }`}
            >
              {prediction.available
                ? `YES, available on ${date}.`
                : `NO, predicted return is ${prediction.predictedReturnDate}.`}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default App;
