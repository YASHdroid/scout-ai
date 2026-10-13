import express from "express";
import axios from "axios";
import researchRouter from "./routes/research";
import authRouter from "./routes/auth";
import { authenticate, AuthRequest } from "./middleware/authMiddleware";
import cors from "cors";
const app = express();

app.use(
  cors({
    origin: "http://localhost:3000",
    methods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allowedHeaders: ["Content-Type", "Authorization"],
  })
);

app.use(express.json());

const PORT = 3001;
const PYTHON_URL = "http://localhost:8000";




app.use("/api/auth", authRouter);

app.use("/api/research", researchRouter);

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