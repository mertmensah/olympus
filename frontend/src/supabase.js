import { createClient } from "@supabase/supabase-js";

const SUPABASE_URL = "https://ckoaboxkgbyjplmyylau.supabase.co";
const SUPABASE_BUCKET = "olympus_media";
const SUPABASE_ANON_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNrb2Fib3hrZ2J5anBsbXl5bGF1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzAyNzI2NDEsImV4cCI6MTc2MTgwODY0MX0.s2QGJ2NE42E1Zy9B47h1hJJUCjuHDLmfQVnVUB1w4-k";

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
  // For private buckets, would need to use signedUrls with auth
  // For now, use public URL as our bucket is private but we handle auth on backend
  return `${SUPABASE_URL}/storage/v1/object/${SUPABASE_BUCKET}/${encodeURIComponent(fileKey)}?token=${SUPABASE_ANON_KEY}`;
}
