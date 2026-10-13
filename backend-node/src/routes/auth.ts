
import { Router } from "express";
import {
  signup,
  login,
  googleLogin,
} from "../services/authService";

const router = Router();

router.post("/signup", async (req, res) => {
  try {
    const { name, email, password } = req.body ?? {};

    if (
      typeof name !== "string" ||
      typeof email !== "string" ||
      typeof password !== "string" ||
      !name.trim() ||
      !email.trim() ||
      !password
    ) {
      return res.status(400).json({
        success: false,
        error: "Name, email, and password are required",
      });
    }

    if (name.trim().length > 100) {
      return res.status(400).json({
        success: false,
        error: "Name must be 100 characters or fewer",
      });
    }

    if (password.length < 8) {
      return res.status(400).json({
        success: false,
        error: "Password must be at least 8 characters",
      });
    }

    const user = await signup(name, email, password);

    return res.status(201).json({
      success: true,
      user,
    });
  } catch (error) {
    console.error("Signup error:", error);

    const code =
      typeof error === "object" && error !== null && "code" in error
        ? (error as { code?: string }).code
        : undefined;

    if (code === "23505") {
      return res.status(409).json({
        success: false,
        error: "An account with this email already exists",
      });
    }

    return res.status(500).json({
      success: false,
      error: "Signup failed",
    });
  }
});

router.post("/login", async (req, res) => {
  try {
    const { email, password } = req.body ?? {};

    if (
      typeof email !== "string" ||
      typeof password !== "string" ||
      !email.trim() ||
      !password
    ) {
      return res.status(400).json({
        success: false,
        error: "Email and password are required",
      });
    }

    const user = await login(email, password);

    return res.json({
      success: true,
      user,
    });
  } catch (error) {
    console.error("Login error:", error);

    return res.status(401).json({
      success: false,
      error: "Invalid email or password",
    });
  }
});

router.post("/google", async (req, res) => {
  try {
    const { credential } = req.body ?? {};

    if (
      typeof credential !== "string" ||
      !credential.trim()
    ) {
      return res.status(400).json({
        success: false,
        error: "Google credential is required",
      });
    }

    const user = await googleLogin(credential);

    return res.json({
      success: true,
      user,
    });
  } catch (error) {
    console.error("Google authentication error:", error);

    const message =
      error instanceof Error ? error.message : "";

    if (
      message === "GOOGLE_CLIENT_ID is missing" ||
      message === "JWT_SECRET is missing"
    ) {
      return res.status(500).json({
        success: false,
        error: "Google authentication is not configured correctly",
      });
    }

    return res.status(401).json({
      success: false,
      error: "Google authentication failed. Please try again.",
    });
  }
});

export default router;
