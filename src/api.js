const RATE_LIMITED_MESSAGE = "You're doing that too much. Please wait a moment and try again.";

/**
 * Parses a fetch Response as JSON, tolerating non-JSON error bodies.
 * Flask-Limiter's default 429 response is a plain HTML page, not JSON, so
 * response.json() throws on it — callers need the 429 case handled before
 * they can safely assume `data` is usable.
 */
export async function parseJsonResponse(response) {
  if (response.status === 429) return { errors: { form: RATE_LIMITED_MESSAGE } };
  try {
    return await response.json();
  } catch {
    return {};
  }
}
