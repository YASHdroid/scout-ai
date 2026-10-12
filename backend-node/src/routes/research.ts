
import { Router, Response } from "express";
import axios from "axios";

import {
  authenticate,
  AuthRequest,
} from "../middleware/authMiddleware";

const router = Router();


router.get(
  "/health",
  authenticate,
  async (_req: AuthRequest, res: Response) => {
    try {
      const response = await axios.get(
        `${PYTHON_URL}/health`,
        { timeout: 5000 }
      );

      return res.json({
        success: true,
        node: "running",
        python: response.data
      });
    } catch (error) {
      return res.status(502).json({
        success: false,
        error: "Python AI service is unavailable"
      });
    }
  }
);


const PYTHON_URL =
  process.env.PYTHON_URL || "http://127.0.0.1:8000";

router.post(
  "/advanced",
  authenticate,
  async (req: AuthRequest, res: Response) => {
    const query =
      typeof req.body?.query === "string"
        ? req.body.query.trim()
        : "";

    if (query.length < 5) {
      return res.status(400).json({
        success: false,
        error: "Research query must be at least 5 characters.",
      });
    }

    if (query.length > 2000) {
      return res.status(400).json({
        success: false,
        error: "Research query cannot exceed 2000 characters.",
      });
    }

    try {
      const response = await axios.post(
        `${PYTHON_URL}/research/advanced`,
        { query },
        {
          timeout: 0,
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      return res.status(200).json(response.data);
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        console.error(
          "Python research service error:",
          error.message
        );

        const pythonStatus = error.response?.status;

        if (
          pythonStatus &&
          pythonStatus >= 400 &&
          pythonStatus < 500
        ) {
          return res.status(pythonStatus).json({
            success: false,
            error:
              "Research request was rejected by the AI service.",
          });
        }
      } else {
        console.error("Advanced research error:", error);
      }

      return res.status(502).json({
        success: false,
        error:
          "Advanced Research service is unavailable or failed.",
      });
    }
  }
);

export default router;
