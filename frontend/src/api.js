import axios from "axios";

export const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
export const api = axios.create({ baseURL: API + "/api" });

// attach the JWT to every request
api.interceptors.request.use((c) => {
  const t = localStorage.getItem("access");
  if (t) c.headers.Authorization = "Bearer " + t;
  return c;
});
api.interceptors.response.use(
  (r) => r,
  (e) => {
    if (e.response?.status === 401 && !e.config.url.includes("auth/login")) {
      localStorage.clear();
      window.location = "/login";
    }
    return Promise.reject(e);
  }
);

const PLACEHOLDER =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    "<svg xmlns='http://www.w3.org/2000/svg' width='200' height='150'><rect width='200' height='150' fill='#e9ecef'/><text x='100' y='80' font-size='14' text-anchor='middle' fill='#6c757d' font-family='sans-serif'>No image</text></svg>"
  );
export const img = (p) => (p ? (p.startsWith("http") ? p : API + p) : PLACEHOLDER);

export const errMsg = (e) => {
  const d = e.response?.data;
  if (!d) return e.message;
  if (typeof d === "string") return "Server error";
  if (Array.isArray(d)) return d.join(" ");
  if (d.detail) return d.detail;
  return Object.entries(d).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(" ") : v}`).join(" | ");
};

// download a protected file (PDF/CSV) with the JWT header
export async function download(url, filename) {
  const r = await api.get(url, { responseType: "blob" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(r.data);
  a.download = filename;
  a.click();
}
