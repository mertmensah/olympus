import { createClient } from "@supabase/supabase-js";

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || "";
const SUPABASE_BUCKET = import.meta.env.VITE_SUPABASE_BUCKET || "olympus_media";
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || "";

function decodeJwtPayload(token) {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) {
      return null;
    }

    const payload = parts[1]
      .replace(/-/g, "+")
      .replace(/_/g, "/")
      .padEnd(Math.ceil(parts[1].length / 4) * 4, "=");

    return JSON.parse(atob(payload));
  } catch {
    return null;
  }
}

function assertSupabaseConfig() {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    throw new Error(
      "Missing Supabase frontend config. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in frontend/.env."
    );
  }

  const payload = decodeJwtPayload(SUPABASE_ANON_KEY);
  if (payload?.exp && Date.now() >= Number(payload.exp) * 1000) {
    throw new Error(
      "VITE_SUPABASE_ANON_KEY is expired. Generate a new publishable/anon key in Supabase and update frontend/.env."
    );
  }
}

assertSupabaseConfig();

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
});

export async function signInWithEmail(email, password) {
  const { data, error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) {
    throw error;
  }
  return data;
}

export async function signUpWithEmail(email, password) {
  const { data, error } = await supabase.auth.signUp({ email, password });
  if (error) {
    throw error;
  }
  return data;
}

export async function signOutUser() {
  const { error } = await supabase.auth.signOut();
  if (error) {
    throw error;
  }
}

export async function getCurrentSession() {
  const { data, error } = await supabase.auth.getSession();
  if (error) {
    throw error;
  }
  return data.session;
}

/**
 * Build a public download URL for a file in Supabase Storage
 * @param {string} fileKey - The file key/path in Supabase (e.g., "job-id/outputs/reconstruction.glb")
 * @returns {string} Access token that can be used to download the file
 */
export function getSupabaseStorageUrl(fileKey) {
  // Supabase public storage download URL format:
  // https://{project_url}/storage/v1/object/public/{bucket}/{path}
  return `${SUPABASE_URL}/storage/v1/object/public/${SUPABASE_BUCKET}/${encodeURIComponent(fileKey)}`;
}

/**
 * Get a signed download URL if the file is in a private bucket
 * @param {string} fileKey - The file key/path
 * @returns {string} Signed URL with token
 */
export function getSignedSupabaseUrl(fileKey) {
  // Legacy helper retained for compatibility. Prefer backend-protected file serving.
  return `${SUPABASE_URL}/storage/v1/object/${SUPABASE_BUCKET}/${encodeURIComponent(fileKey)}?token=${SUPABASE_ANON_KEY}`;
}
