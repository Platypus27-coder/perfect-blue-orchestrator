import { useState, useRef } from "react";
import { RefreshCw, ExternalLink, Play, Square } from "lucide-react";
import { claw3dBaseUrl } from "../../lib/appConfig";

export default function OfficeScreen() {
  const [running, setRunning] = useState(true);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const claw3dUrl = `${claw3dBaseUrl}/office`;

  function refreshIframe() {
    const el = iframeRef.current;
    if (el) {
      const src = el.src;
      el.src = "";
      setTimeout(() => { el.src = src; }, 50);
    }
  }

  return (
    <div className="office-container">
      <div className="office-toolbar">
        <div className="office-toolbar-left">
          <h2 className="office-toolbar-title">Office</h2>
          <span className={`status-badge ${running ? "online" : "offline"}`}>
            <span className={`status-dot-inline ${running ? "online" : "offline"}`} />
            {running ? "Running" : "Stopped"}
          </span>
        </div>
        <div className="office-toolbar-right">
          <button className="btn btn-sm btn-ghost" onClick={() => setRunning(!running)}>
            {running ? <Square size={14} /> : <Play size={14} />}
            {running ? "Stop" : "Start"}
          </button>
          {running && (
            <>
              <button className="office-toolbar-btn" onClick={refreshIframe} title="Refresh">
                <RefreshCw size={16} />
              </button>
              <button className="office-toolbar-btn" onClick={() => window.open(claw3dUrl, "_blank")} title="Open in Browser">
                <ExternalLink size={16} />
              </button>
            </>
          )}
        </div>
      </div>
      <div className="office-content">
        {running ? (
          <iframe
            ref={iframeRef}
            src={claw3dUrl}
            title="Claw3D Office"
          />
        ) : (
          <div className="office-center">
            <p className="office-muted">Click Start to launch the Claw3D office</p>
          </div>
        )}
      </div>
    </div>
  );
}
