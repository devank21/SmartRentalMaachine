import React, { useState, useEffect } from "react";
import axios from "axios";
import { Line } from "react-chartjs-2";

// NOTE: The leaflet (map) imports were removed as they were not being used in the current UI
// and were causing compilation errors.
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

// --- Main App Component ---
function App() {
  const [equipmentData, setEquipmentData] = useState([]);
  const [selectedEquipment, setSelectedEquipment] = useState(null);
  const [error, setError] = useState(null);
  const API_BASE_URL = "http://127.0.0.1:5000/api";

  useEffect(() => {
    axios
      .get(`${API_BASE_URL}/equipment`)
      .then((response) => {
        setEquipmentData(response.data);
      })
      .catch((err) => {
        console.error("Error fetching equipment data:", err);
        setError(
          "Could not load equipment data. Is the backend server running?"
        );
      });
  }, []);

  const handleSelectEquipment = (equipment) => {
    setSelectedEquipment(equipment);
  };

  const handleBackToList = () => {
    setSelectedEquipment(null);
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="logo">CAT</div>
        <h1>Smart Fleet Command Center</h1>
      </header>
      <main className="main-content">
        {error ? (
          <div className="error-message-full-page">{error}</div>
        ) : selectedEquipment ? (
          <EquipmentDetail
            equipment={selectedEquipment}
            onBack={handleBackToList}
            apiBaseUrl={API_BASE_URL}
          />
        ) : (
          <EquipmentTable
            equipment={equipmentData}
            onSelect={handleSelectEquipment}
          />
        )}
      </main>
    </div>
  );
}

// --- EquipmentTable (Full Page List) ---
const EquipmentTable = ({ equipment, onSelect }) => {
  return (
    <div className="table-container-full-page">
      <div className="card-header">
        <h2>Master Equipment List</h2>
        <p>Click on any asset to view its detailed forecast and history.</p>
      </div>
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Type</th>
              <th>Status</th>
              <th>Engine Hours</th>
              <th>Fuel Level</th>
              <th>Location</th>
            </tr>
          </thead>
          <tbody>
            {equipment.map((item) => {
              const statusClass = `status-${item.Status.toLowerCase().replace(
                " ",
                "-"
              )}`;
              return (
                <tr key={item.EquipmentID} onClick={() => onSelect(item)}>
                  <td className="id-cell">{item.EquipmentID}</td>
                  <td>{item.Type}</td>
                  <td>
                    <span className={`status-badge ${statusClass}`}>
                      {item.Status}
                    </span>
                  </td>
                  <td>{item.EngineHours}</td>
                  <td>{item.FuelLevel}%</td>
                  <td>{`${item.Latitude.toFixed(2)}, ${item.Longitude.toFixed(
                    2
                  )}`}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// --- EquipmentDetail (Drill-down View) ---
const EquipmentDetail = ({ equipment, onBack, apiBaseUrl }) => {
  const [forecastData, setForecastData] = useState(null);
  const [forecastError, setForecastError] = useState(null);

  useEffect(() => {
    setForecastData(null); // Reset on new selection
    setForecastError(null);
    axios
      .get(`${apiBaseUrl}/forecast/${equipment.EquipmentID}`)
      .then((response) => {
        setForecastData(response.data);
      })
      .catch((err) => {
        console.error("Error fetching forecast data:", err);
        setForecastError(
          err.response?.data?.error || "Could not load forecast data."
        );
      });
  }, [equipment.EquipmentID, apiBaseUrl]);

  return (
    <div className="detail-container">
      <button onClick={onBack} className="back-button">
        ← Back to Full List
      </button>
      <div className="detail-header">
        <h2>
          Rental Forecast:{" "}
          <span className="detail-id">{equipment.EquipmentID}</span>
        </h2>
        <p>
          {equipment.Type} - Last known status: {equipment.Status}
        </p>
      </div>
      <div className="chart-container">
        {forecastError ? (
          <div className="loading-message error-message">{forecastError}</div>
        ) : forecastData ? (
          <ForecastChart data={forecastData} />
        ) : (
          <div className="loading-message">Generating forecast...</div>
        )}
      </div>
    </div>
  );
};

// --- ForecastChart Component (reusable) ---
const ForecastChart = ({ data }) => {
  const chartData = {
    labels: data.historical.dates, // Use historical dates for the full range
    datasets: [
      {
        label: "Historical Rentals",
        data: data.historical.values,
        borderColor: "rgba(255, 255, 255, 0.5)",
        backgroundColor: "rgba(255, 255, 255, 0.1)",
        borderWidth: 1.5,
        pointRadius: 2,
        tension: 0.3,
        fill: true,
        stepped: true,
      },
      {
        label: "Forecasted Demand",
        // Align forecast data with historical data
        data: [
          ...new Array(data.historical.values.length).fill(null),
          ...data.forecast.values,
        ],
        borderColor: "var(--primary-yellow)",
        borderWidth: 2.5,
        pointRadius: 2,
        tension: 0.3,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "top",
        align: "end",
        labels: { color: "#ffffff", boxWidth: 12, padding: 20 },
      },
    },
    scales: {
      x: {
        ticks: { color: "#a0a0a0" },
        grid: { color: "rgba(255, 255, 255, 0.05)" },
      },
      y: {
        ticks: { color: "#a0a0a0", stepSize: 1 },
        grid: { color: "rgba(255, 255, 255, 0.1)" },
        beginAtZero: true,
        title: {
          display: true,
          text: "Number of Daily Rentals",
          color: "#ffffff",
        },
      },
    },
  };

  return (
    <div className="chart-wrapper">
      <Line data={chartData} options={chartOptions} />
    </div>
  );
};

export default App;
