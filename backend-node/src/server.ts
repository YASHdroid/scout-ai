import express from "express";
import axios from "axios";
import authRouter from "./routes/auth";
import { authenticate, AuthRequest } from "./middleware/authMiddleware";
const app = express();

const PORT = 3000;
const PYTHON_URL = "http://localhost:8000";

app.use(express.json());


app.use("/api/auth", authRouter);

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