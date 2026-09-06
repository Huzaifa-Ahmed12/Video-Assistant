const BASE_URL = "http://localhost:8000/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Request failed (${res.status}): ${text}`);
  }
  const contentType = res.headers.get("content-type") || "";
  return contentType.includes("application/json") ? res.json() : res.text();
}

export const api = {
  listMeetings: () => request("/meetings/"),
  getMeeting: (id) => request(`/meetings/${id}/`),
  uploadMeeting: (formData) =>
    request("/meetings/", { method: "POST", body: formData, headers: {} }),
  deleteMeeting: (id) => request(`/meetings/${id}/`, { method: "DELETE" }),
  getTranscript: (id) => request(`/meetings/${id}/transcript/`),
  sendChatMessage: (meetingId, message) =>
    request(`/meetings/${meetingId}/chat/`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  getChatHistory: (meetingId) => request(`/meetings/${meetingId}/chat/`),
};
