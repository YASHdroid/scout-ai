import express from "express";
import axios from "axios";

const app = express();

const PORT = 3000;
const PYTHON_URL = "http://localhost:8000";

app.use(express.json());

app.get("/health", (req, res) => {
  res.json({
    status: "Node backend is running"
  });
});

app.post("/api/research", async (req, res) => {
  try {
const response = await axios.post(
  `${PYTHON_URL}/research`,
  req.body
);
    res.json({
      success: true,
      data: response.data
    });
  } catch (error) {
    console.error("Python service error:", error);

    res.status(500).json({
      success: false,
      error: "AI service unavailable"
    });
  }
});

app.listen(PORT, () => {
  console.log(`Node server running on http://localhost:${PORT}`);
});