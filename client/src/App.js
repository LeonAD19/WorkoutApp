import { useEffect, useState } from "react";

function App() {
  const [message, setMessage] = useState("");

  useEffect(() => {
    // Use relative URL so it works in both dev and production
    const apiUrl = process.env.REACT_APP_API_URL || "/api";
    
    fetch(apiUrl)
      .then((res) => res.json())
      .then((data) => setMessage(data.message))
      .catch((err) => console.error("Error fetching API:", err));
  }, []);

  return (
    <div style={{ textAlign: "center", marginTop: "50px" }}>
      <h1>Flask + React Connected ✅</h1>
      <p>{message || "Loading..."}</p>
    </div>
  );
}

export default App;
