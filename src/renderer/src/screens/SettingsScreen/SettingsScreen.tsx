import { Info } from "lucide-react";
import logoImg from "../../assets/logo.jpg";
import { claw3dBaseUrl } from "../../lib/appConfig";
import { runtimeBaseUrl } from "../../lib/runtimeApi";

export default function SettingsScreen() {
  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Settings</h1>
          <p className="page-subtitle">Configure your workspace</p>
        </div>
      </div>
      <div className="page-body">
        <div className="card" style={{ maxWidth: 600 }}>
          <div className="card-header">
            <h3 className="card-title">About</h3>
            <Info size={16} style={{ color: "var(--text-muted)" }} />
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <img src={logoImg} alt="Logo" style={{ width: 64, height: 64, borderRadius: 12, objectFit: "cover" }} />
            <div>
              <div style={{ fontSize: 18, fontWeight: 700 }}>PerfectBlue Agent</div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 2 }}>
                Multi-Agent Control Dashboard
              </div>
              <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
                Version 0.1.0 • Built with React + Vite
              </div>
            </div>
          </div>
        </div>

        <div className="card" style={{ maxWidth: 600, marginTop: 16 }}>
          <div className="card-header">
            <h3 className="card-title">Office (Claw3D)</h3>
          </div>
          <div className="form-group">
            <label className="form-label">Claw3D URL</label>
            <input className="form-input" value={claw3dBaseUrl} readOnly />
          </div>
          <p style={{ fontSize: 12, color: "var(--text-muted)" }}>
            Configure with <code style={{ background: "var(--bg-hover)", padding: "2px 6px", borderRadius: 4 }}>VITE_CLAW3D_URL</code> before starting the dashboard.
          </p>
        </div>

        <div className="card" style={{ maxWidth: 600, marginTop: 16 }}>
          <div className="card-header">
            <h3 className="card-title">PerfectBlue Runtime</h3>
          </div>
          <div className="form-group">
            <label className="form-label">Runtime URL</label>
            <input className="form-input" value={runtimeBaseUrl} readOnly />
          </div>
          <p style={{ fontSize: 12, color: "var(--text-muted)" }}>
            Configure URL and token with <code style={{ background: "var(--bg-hover)", padding: "2px 6px", borderRadius: 4 }}>VITE_PERFECTBLUE_RUNTIME_URL</code> and <code style={{ background: "var(--bg-hover)", padding: "2px 6px", borderRadius: 4 }}>VITE_PERFECTBLUE_RUNTIME_TOKEN</code>.
          </p>
        </div>
      </div>
    </>
  );
}
