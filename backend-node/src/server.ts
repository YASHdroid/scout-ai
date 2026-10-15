
import express from "express";
import researchRouter from "./routes/research";
import authRouter from "./routes/auth";
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

app.use("/api/auth", authRouter);
app.use("/api/research", researchRouter);

app.listen(PORT, () => {
  console.log(`Node server running on http://localhost:${PORT}`);
});
