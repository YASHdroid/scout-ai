import { Request, Response, NextFunction } from "express";
import jwt, { JwtPayload } from "jsonwebtoken";

export interface AuthRequest extends Request {
  user?: {
    id: number;
    email: string;
  };
}

export function authenticate(
  req: AuthRequest,
  res: Response,
  next: NextFunction
) {
  const authHeader = req.headers.authorization;

  if (!authHeader) {
    return res.status(401).json({
      success: false,
      error: "Authentication token required"
    });
  }

  const token = authHeader.split(" ")[1];

  if (!token) {
    return res.status(401).json({
      success: false,
      error: "Authentication token required"
    });
  }

  const secret = process.env.JWT_SECRET;

  if (!secret) {
    return res.status(500).json({
      success: false,
      error: "JWT_SECRET is missing"
    });
  }

  try {
    const decoded = jwt.verify(token, secret) as JwtPayload;

    if (
      typeof decoded.id !== "number" ||
      typeof decoded.email !== "string"
    ) {
      return res.status(401).json({
        success: false,
        error: "Invalid token"
      });
    }

    req.user = {
      id: decoded.id,
      email: decoded.email
    };

    next();
  } catch (error) {
    return res.status(401).json({
      success: false,
      error: "Invalid or expired token"
    });
  }
}