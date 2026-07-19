export const claw3dBaseUrl = (
  import.meta.env.VITE_CLAW3D_URL ||
  `http://${window.location.hostname || "127.0.0.1"}:3000`
).replace(/\/$/, "");
