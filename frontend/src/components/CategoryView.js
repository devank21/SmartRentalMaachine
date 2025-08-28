import React, { useState, useEffect } from "react";
import axios from "axios";

const API_BASE_URL = "http://127.0.0.1:5000/api";

const CategoryView = ({ category, navigateTo }) => {
  const [equipment, setEquipment] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeFilter, setActiveFilter] = useState("All"); // State for the filter

  useEffect(() => {
    setIsLoading(true);
    setEquipment([]);
    setError("");

    axios
      .get(`${API_BASE_URL}/equipment/type/${category}`)
      .then((res) => {
        if (res.data && Array.isArray(res.data.data)) {
          setEquipment(res.data.data);
        } else {
          setError("Received invalid data format from the server.");
        }
      })
      .catch((err) => {
        console.error(`Error fetching equipment for ${category}:`, err);
        setError("Could not load equipment details.");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [category]);

  // Filter the equipment based on the active filter
  const filteredEquipment = equipment.filter((item) => {
    if (activeFilter === "All") {
      return true;
    }
    // Handle "In-Use" case
    if (activeFilter === "In-Use") {
      return item.Status === "In-Use";
    }
    return item.Status === activeFilter;
  });

  if (isLoading)
    return <div className="loading">Loading {category} fleet...</div>;
  if (error) return <div className="error-message">{error}</div>;

  return (
    <div className="view-container">
      <button className="back-button" onClick={() => navigateTo("dashboard")}>
        &larr; Back to Dashboard
      </button>
      <div className="category-header">
        <h2>{category} Fleet</h2>
        <div className="filter-controls">
          <button
            onClick={() => setActiveFilter("All")}
            className={activeFilter === "All" ? "active" : ""}
          >
            All
          </button>
          <button
            onClick={() => setActiveFilter("Available")}
            className={activeFilter === "Available" ? "active" : ""}
          >
            Available
          </button>
          <button
            onClick={() => setActiveFilter("In-Use")}
            className={activeFilter === "In-Use" ? "active" : ""}
          >
            In-Use
          </button>
          <button
            onClick={() => setActiveFilter("Maintenance")}
            className={activeFilter === "Maintenance" ? "active" : ""}
          >
            Maintenance
          </button>
        </div>
      </div>

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
            {filteredEquipment.length > 0 ? (
              filteredEquipment.map((item) => (
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
              ))
            ) : (
              <tr>
                <td colSpan="5" style={{ textAlign: "center" }}>
                  No equipment matches the filter "{activeFilter}".
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default CategoryView;
