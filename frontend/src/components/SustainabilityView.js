import React, { useState, useEffect } from "react";
import axios from "axios";

const API_BASE_URL = "http://127.0.0.1:5000/api";

const SustainabilityView = ({ navigateTo }) => {
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    axios
      .get(`${API_BASE_URL}/sustainability/report`)
      .then((res) => {
        if (res.data && res.data.data) {
          setReport(res.data.data);
        } else {
          setError("Received invalid data format from server.");
        }
      })
      .catch((err) => {
        console.error("Error fetching sustainability report:", err);
        setError("Could not connect to the backend server.");
      });
  }, []);

  if (error) return <div className="error-message">{error}</div>;
  if (!report)
    return <div className="loading">Loading Sustainability Report...</div>;

  return (
    <div className="view-container">
      <button className="back-button" onClick={() => navigateTo("dashboard")}>
        &larr; Back to Dashboard
      </button>
      <h2>Fleet Sustainability Report</h2>
      <p>
        This report provides an overview of the fleet's environmental impact
        based on operational data.
      </p>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Equipment Type</th>
              <th>Total Engine Hours</th>
              <th>Avg. Fuel Level (%)</th>
              <th>Estimated CO₂e Emissions (kg)</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(report).map(([type, data]) => (
              <tr key={type}>
                <td>{type}</td>
                <td>{data.total_engine_hours.toLocaleString()}</td>
                <td>{data.average_fuel_level}</td>
                <td>{data.total_emissions_kg_co2e.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default SustainabilityView;
