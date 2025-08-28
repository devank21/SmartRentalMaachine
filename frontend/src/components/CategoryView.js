import React, { useState, useEffect } from "react";
import axios from "axios";

const API_BASE_URL = "http://127.0.0.1:5000/api";

const CategoryView = ({ category, navigateTo }) => {
  const [equipment, setEquipment] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    // Reset state on category change
    setEquipment([]);
    setError("");

    axios
      .get(`${API_BASE_URL}/equipment/type/${category}`)
      .then((res) => {
        // FIX: More robust check for the data structure
        if (res.data && Array.isArray(res.data.data)) {
          setEquipment(res.data.data);
        } else {
          // This error message will now only appear for genuine server issues
          setError("Received invalid data format from the server.");
          console.error("Invalid data structure:", res.data);
        }
      })
      .catch((err) => {
        console.error(`Error fetching equipment for ${category}:`, err);
        setError(
          "Could not load equipment details. Please ensure the backend is running."
        );
      });
  }, [category]);

  if (error) return <div className="error-message">{error}</div>;
  if (equipment.length === 0 && !error)
    return <div className="loading">Loading {category} fleet...</div>;

  return (
    <div className="view-container">
      <button className="back-button" onClick={() => navigateTo("dashboard")}>
        &larr; Back to Dashboard
      </button>
      <h2>{category} Fleet</h2>
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Equipment ID</th>
              <th>Status</th>
              <th>Customer</th>
              <th>Job Site</th>
              <th>Expected Return</th>
            </tr>
          </thead>
          <tbody>
            {equipment.map((item) => (
              <tr
                key={item.EquipmentID}
                onClick={() =>
                  navigateTo("vehicle", {
                    equipmentId: item.EquipmentID,
                    category,
                  })
                }
              >
                <td>{item.EquipmentID}</td>
                <td>
                  <span
                    className={`status-badge status-${item.Status.toLowerCase().replace(
                      "-",
                      ""
                    )}`}
                  >
                    {item.Status}
                  </span>
                </td>
                <td>{item.Customer || "N/A"}</td>
                <td>{item.JobSiteName || "N/A"}</td>
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

export default CategoryView;
