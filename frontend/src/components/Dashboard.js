import React, { useState, useEffect } from "react";
import axios from "axios";

const API_BASE_URL = "http://127.0.0.1:5000/api";

const Dashboard = ({ navigateTo }) => {
  const [summary, setSummary] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    axios
      .get(`${API_BASE_URL}/summary`)
      .then((res) => {
        if (res.data && Array.isArray(res.data.data)) {
          setSummary(res.data.data);
        } else {
          setError("Received invalid data format from server.");
        }
      })
      .catch((err) => {
        console.error("Error fetching summary:", err);
        setError("Could not connect to the backend server.");
      });
  }, []);

  if (error) return <div className="error-message">{error}</div>;
  if (summary.length === 0)
    return <div className="loading">Loading fleet summary...</div>;

  return (
    <div className="dashboard-grid">
      {summary.map(({ category, statuses }) => (
        <div
          key={category}
          className="summary-card"
          onClick={() => navigateTo("category", { category })}
        >
          <h2>{category}</h2>
          <p className="total-count">{statuses.Total || 0} Total Units</p>
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

export default Dashboard;
