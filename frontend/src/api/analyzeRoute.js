/**
 * Sends a POST request to analyze-route endpoint.
 * @param {object} params
 * @returns {Promise<object>}
 */
export async function analyzeRoute(params) {
  const apiUrl = import.meta.env.VITE_API_URL;
  if (!apiUrl) {
    throw new Error("VITE_API_URL is not configured. Add it to .env and restart.");
  }

  const endpoint = `${apiUrl.replace(/\/$/, "")}/analyze-route`;

  let response;
  try {
    response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(params),
    });
  } catch (networkErr) {
    throw new Error("Network error — check your connection.");
  }

  let data;
  try {
    data = await response.json();
  } catch (parseErr) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  if (!response.ok) {
    const errorMsg =
      data && data.error
        ? data.error
        : `Request failed with status ${response.status}`;
    throw new Error(errorMsg);
  }

  return data;
}
