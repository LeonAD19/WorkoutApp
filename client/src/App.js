import { useEffect, useState } from "react";

function App() {
  const [message, setMessage] = useState("");

useEffect(() => {
  fetch("http://127.0.0.1:5000/api")
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
