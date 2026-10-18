
import { Router, Response } from "express";
import axios from "axios";
import multer from "multer";
import FormData from "form-data";

import {
  authenticate,
  AuthRequest,
} from "../middleware/authMiddleware";

const router = Router();

const PYTHON_URL =
  process.env.PYTHON_URL || "http://127.0.0.1:8000";

const pdfUpload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 25 * 1024 * 1024,
  },
  fileFilter: (_req, file, callback) => {
    const isPdf =
      file.mimetype === "application/pdf" ||
      file.originalname.toLowerCase().endsWith(".pdf");

    callback(null, isPdf);
  },
});

// Standard Research
router.post(
  "/",
  authenticate,
  async (req: AuthRequest, res: Response) => {
    const query =
      typeof req.body?.query === "string"
        ? req.body.query.trim()
        : "";

    if (query.length < 5 || query.length > 2000) {
      return res.status(400).json({
        success: false,
        error: "Query must contain 5 to 2000 characters.",
      });
    }

    try {
      const response = await axios.post(
        `${PYTHON_URL}/research`,
        { query },
        { timeout: 180000 }
      );

      return res.status(200).json(response.data);
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        console.error("Standard Research error:", error.message);

        const status = error.response?.status;
        const detail = error.response?.data?.detail;

        if (status && status >= 400 && status < 500) {
          return res.status(status).json({
            success: false,
            error:
              typeof detail === "string"
                ? detail
                : "The AI service rejected the request.",
          });
        }
      } else {
        console.error("Standard Research error:", error);
      }

      return res.status(502).json({
        success: false,
        error: "Standard Research service failed.",
      });
    }
  }
);

// Upload and index a PDF
router.post(
  "/documents",
  authenticate,
  pdfUpload.single("file"),
  async (req: AuthRequest, res: Response) => {
    if (!req.file) {
      return res.status(400).json({
        success: false,
        error: "Please select a valid PDF file.",
      });
    }

    try {
      const form = new FormData();

      form.append("file", req.file.buffer, {
        filename: req.file.originalname,
        contentType: "application/pdf",
      });

      const response = await axios.post(
        `${PYTHON_URL}/documents`,
        form,
        {
          headers: form.getHeaders(),
          timeout: 300000,
          maxBodyLength: Infinity,
          maxContentLength: Infinity,
        }
      );

      return res.status(201).json({
        success: true,
        ...response.data,
      });
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        console.error("PDF upload error:", error.message);

        return res.status(502).json({
          success: false,
          error:
            "PDF upload or indexing failed. Check the Python service logs.",
        });
      }

      console.error("PDF upload error:", error);

      return res.status(500).json({
        success: false,
        error: "Could not process the PDF.",
      });
    }
  }
);

// Create a conversation linked to the uploaded document
router.post(
  "/conversations",
  authenticate,
  async (req: AuthRequest, res: Response) => {
    const documentId = Number(req.body?.document_id);

    if (!Number.isInteger(documentId) || documentId <= 0) {
      return res.status(400).json({
        success: false,
        error: "A valid document_id is required.",
      });
    }

    try {
      const response = await axios.post(
        `${PYTHON_URL}/conversations`,
        { document_id: documentId },
        { timeout: 15000 }
      );

      return res.status(201).json({
        success: true,
        ...response.data,
      });
    } catch (error: unknown) {
      console.error("Conversation creation error:", error);

      return res.status(502).json({
        success: false,
        error: "Could not create the document conversation.",
      });
    }
  }
);

// Chat with the uploaded PDF
router.post(
  "/chat",
  authenticate,
  async (req: AuthRequest, res: Response) => {
    const conversationId = Number(req.body?.conversation_id);
    const query =
      typeof req.body?.query === "string"
        ? req.body.query.trim()
        : "";

    if (!Number.isInteger(conversationId) || conversationId <= 0) {
      return res.status(400).json({
        success: false,
        error: "A valid conversation_id is required.",
      });
    }

    if (query.length < 1 || query.length > 2000) {
      return res.status(400).json({
        success: false,
        error: "Query must contain 1 to 2000 characters.",
      });
    }

    try {
      const response = await axios.post(
        `${PYTHON_URL}/chat`,
        {
          conversation_id: conversationId,
          query,
        },
        { timeout: 180000 }
      );

      if (response.data?.error) {
        return res.status(404).json({
          success: false,
          error: response.data.error,
        });
      }

      return res.status(200).json(response.data);
    } catch (error: unknown) {
      console.error("Document chat error:", error);

      return res.status(502).json({
        success: false,
        error: "Could not answer the question about this PDF.",
      });
    }
  }
);

// Research service health check
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
        python: response.data,
      });
    } catch (error) {
      console.error("Research health check failed:", error);

      return res.status(502).json({
        success: false,
        error: "Python AI service is unavailable.",
      });
    }
  }
);

// Deep Research

router.post(
  "/advanced",
  authenticate,
  async (req: AuthRequest, res: Response) => {
    const query =
      typeof req.body?.query === "string"
        ? req.body.query.trim()
        : "";

    const rawDocumentId = req.body?.document_id;
    const documentId =
      rawDocumentId === undefined || rawDocumentId === null
        ? undefined
        : Number(rawDocumentId);

    if (query.length < 5 || query.length > 2000) {
      return res.status(400).json({
        success: false,
        error: "Query must contain 5 to 2000 characters.",
      });
    }

    if (
      documentId !== undefined &&
      (!Number.isInteger(documentId) || documentId <= 0)
    ) {
      return res.status(400).json({
        success: false,
        error: "document_id must be a positive integer.",
      });
    }

    try {
      const response = await axios.post(
        `${PYTHON_URL}/research/advanced`,
        {
          query,
          ...(documentId !== undefined
            ? { document_id: documentId }
            : {}),
        },
        {
          timeout: 0,
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      return res.status(200).json(response.data);
    } catch (error: unknown) {
      console.error("Deep Research error:", error);

      return res.status(502).json({
        success: false,
        error: "Advanced Research service failed.",
      });
    }
  }
);

export default router;
