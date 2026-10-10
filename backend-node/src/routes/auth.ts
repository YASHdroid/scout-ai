import { Router } from "express";
import { signup, login } from "../services/authService";

const router = Router();

router.post("/signup", async (req, res) => {
  try {
    const { email, password } = req.body;

    const user = await signup(email, password);

    res.status(201).json({
      success: true,
      user
    });
  } catch (error) {
    console.error("Signup error:", error);

    res.status(500).json({
      success: false,
      error: "Signup failed"
    });
  }
});

router.post("/login", async (req, res) => {
  try {
    const { email, password } = req.body;

    const user = await login(
      email,
      password
    );

    res.json({
      success: true,
      user
    });
  } catch (error) {
    console.error("Login error:", error);

    res.status(401).json({
      success: false,
      error: "Invalid email or password"
    });
  }
});

export default router;