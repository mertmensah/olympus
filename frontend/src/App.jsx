import { useMemo, useState } from "react";
import HomePage from "./pages/HomePage";
import UploadPage from "./pages/UploadPage";
import ViewerPage from "./pages/ViewerPage";

const TABS = {
  HOME: "home",
  UPLOAD: "upload",
  VIEWER: "viewer"
};

export default function App() {
  const [tab, setTab] = useState(TABS.HOME);
  const [activeJob, setActiveJob] = useState(null);

  const content = useMemo(() => {
    if (tab === TABS.UPLOAD) {
      return <UploadPage onJobCreated={setActiveJob} onJumpToViewer={() => setTab(TABS.VIEWER)} />;
    }

    if (tab === TABS.VIEWER) {
      return <ViewerPage activeJob={activeJob} />;
    }

    return <HomePage onStart={() => setTab(TABS.UPLOAD)} />;
  }, [tab, activeJob]);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <strong>Olympus</strong>
          <span>Digital Likeness Platform</span>
        </div>
        <nav className="tabs">
          <button className={tab === TABS.HOME ? "active" : ""} onClick={() => setTab(TABS.HOME)}>
            Home
          </button>
          <button className={tab === TABS.UPLOAD ? "active" : ""} onClick={() => setTab(TABS.UPLOAD)}>
            Upload
          </button>
          <button className={tab === TABS.VIEWER ? "active" : ""} onClick={() => setTab(TABS.VIEWER)}>
            Viewer
          </button>
        </nav>
      </header>
      <main className="content">{content}</main>
    </div>
  );
}
