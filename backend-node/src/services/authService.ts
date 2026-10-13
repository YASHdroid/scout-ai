
import bcrypt from "bcryptjs";
import pool from "../db";
import jwt from "jsonwebtoken";
import { randomBytes } from "crypto";
import { OAuth2Client } from "google-auth-library";

const googleClient = new OAuth2Client();

type AuthUser = {
  id: number;
  email: string;
};

function createToken(user: AuthUser) {
  const secret = process.env.JWT_SECRET;

  if (!secret) {
    throw new Error("JWT_SECRET is missing");
  }

  const token = jwt.sign(
    { id: user.id, email: user.email },
    secret,
    { expiresIn: "7d" }
  );

  return {
    id: user.id,
    email: user.email,
    token,
  };
}

export async function signup(
  name: string,
  email: string,
  password: string
) {
  const normalizedName = name.trim();
  const normalizedEmail = email.trim().toLowerCase();

  if (!normalizedName || !normalizedEmail || !password) {
    throw new Error("Name, email, and password are required");
  }

  if (normalizedName.length > 100) {
    throw new Error("Name must be 100 characters or fewer");
  }

  if (password.length < 8) {
    throw new Error("Password must be at least 8 characters");
  }

  const passwordHash = await bcrypt.hash(password, 10);

  const result = await pool.query(
    `INSERT INTO users (name, email, password_hash)
     VALUES ($1, $2, $3)
     RETURNING id, name, email, created_at`,
    [normalizedName, normalizedEmail, passwordHash]
  );

  return result.rows[0];
}

export async function login(
  email: string,
  password: string
) {
  const normalizedEmail = email.trim().toLowerCase();

  const result = await pool.query(
    `SELECT id, email, password_hash
     FROM users
     WHERE LOWER(email) = $1
     LIMIT 1`,
    [normalizedEmail]
  );

  if (result.rows.length === 0) {
    throw new Error("Invalid email or password");
  }

  const user = result.rows[0];

  const valid = await bcrypt.compare(
    password,
    user.password_hash
  );

  if (!valid) {
    throw new Error("Invalid email or password");
  }

  return createToken(user);
}

export async function googleLogin(credential: string) {
  if (!credential || typeof credential !== "string") {
    throw new Error("Google credential is required");
  }

  const clientId = process.env.GOOGLE_CLIENT_ID;

  if (!clientId) {
    throw new Error("GOOGLE_CLIENT_ID is missing");
  }

  // Verify Google's ID token on the backend.
  const ticket = await googleClient.verifyIdToken({
    idToken: credential,
    audience: clientId,
  });

  const payload = ticket.getPayload();

  if (
    !payload?.sub ||
    !payload.email ||
    payload.email_verified !== true
  ) {
    throw new Error("Google account email is not verified");
  }

  const googleSub = payload.sub;
  const email = payload.email.trim().toLowerCase();

  // 1. Check whether this Google account is already linked.
  let result = await pool.query(
    `SELECT id, email
     FROM users
     WHERE google_sub = $1
     LIMIT 1`,
    [googleSub]
  );

  if (result.rows.length > 0) {
    return createToken(result.rows[0]);
  }

  // 2. Check whether the email already has a Scout account.
  result = await pool.query(
    `SELECT id, email, google_sub
     FROM users
     WHERE LOWER(email) = $1
     LIMIT 1`,
    [email]
  );

  const existingUser = result.rows[0];

  if (existingUser) {
    if (
      existingUser.google_sub &&
      existingUser.google_sub !== googleSub
    ) {
      throw new Error(
        "This email is linked to a different Google account"
      );
    }

    // Link the verified Google account to the existing email.
    result = await pool.query(
      `UPDATE users
       SET google_sub = $1,
           name = COALESCE(
             NULLIF(name, ''),
             $2
           )
       WHERE id = $3
         AND (google_sub IS NULL OR google_sub = $1)
       RETURNING id, email`,
      [
        googleSub,
        (payload.name || email.split("@")[0]).slice(0, 100),
        existingUser.id,
      ]
    );

    if (result.rows.length === 0) {
      throw new Error("Unable to link this Google account");
    }

    return createToken(result.rows[0]);
  }

  // 3. Create a new Google-only account.
  const name =
    (payload.name || email.split("@")[0]).slice(0, 100);

  const randomPassword = randomBytes(32).toString("hex");
  const passwordHash = await bcrypt.hash(randomPassword, 10);

  result = await pool.query(
    `INSERT INTO users
       (name, email, password_hash, google_sub)
     VALUES ($1, $2, $3, $4)
     RETURNING id, email`,
    [name, email, passwordHash, googleSub]
  );

  return createToken(result.rows[0]);
}
