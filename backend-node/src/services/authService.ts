import bcrypt from "bcryptjs";
import pool from "../db";
import jwt from "jsonwebtoken";

export async function signup(
  email: string,
  password: string
) {
  const passwordHash = await bcrypt.hash(
    password,
    10
  );



  const result = await pool.query(
    `
    INSERT INTO users
    (email, password_hash)
    VALUES ($1, $2)
    RETURNING id, email, created_at
    `,
    [
      email,
      passwordHash
    ]
  );

  return result.rows[0];
}
export async function login(
  email: string,
  password: string
) {
  const result = await pool.query(
    `
    SELECT id, email, password_hash
    FROM users
    WHERE email = $1
    `,
    [email]
  );

  if (result.rows.length === 0) {
    throw new Error("Invalid email or password");
  }

  const user = result.rows[0];

  const isPasswordValid = await bcrypt.compare(
    password,
    user.password_hash
  );

  if (!isPasswordValid) {
    throw new Error("Invalid email or password");
  }

  const secret = process.env.JWT_SECRET;

  if (!secret) {
    throw new Error("JWT_SECRET is missing");
  }

  const token = jwt.sign(
    {
      id: user.id,
      email: user.email
    },
    secret,
    {
      expiresIn: "7d"
    }
  );

  return {
    id: user.id,
    email: user.email,
    token
  };
}