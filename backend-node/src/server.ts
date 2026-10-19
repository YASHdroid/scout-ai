
import express from "express";
import researchRouter from "./routes/research";
import authRouter from "./routes/auth";
import cors from "cors";

const app = express();

app.use(
  cors({
    origin: [
      "http://localhost:3000",
      "https://scout-ai-umber.vercel.app",
    ],
    credentials: true,
  })
);

app.use(express.json());

const PORT = Number(process.env.PORT) || 3001;

app.use("/api/auth", authRouter);
app.use("/api/research", researchRouter);

app.listen(PORT, "0.0.0.0", () => {
  console.log(`Node server running on port ${PORT}`);
});