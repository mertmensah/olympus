import { useMemo, useState } from "react";
import HomePage from "./pages/HomePage";
import UploadPage from "./pages/UploadPage";
import MyPersonaPage from "./pages/MyPersonaPage";
import CommunityPage from "./pages/CommunityPage";
import ConnectionsPage from "./pages/ConnectionsPage";

const TABS = {
  HOME: "home",
  MY_PERSONA: "my-persona",
  COMMUNITY: "community",
  CONNECTIONS: "connections",
  BUILD_PERSONA: "build-persona"
};

export default function App() {
  const [tab, setTab] = useState(TABS.HOME);
  const [activeJob, setActiveJob] = useState(null);

  const content = useMemo(() => {
    if (tab === TABS.MY_PERSONA) {
      return <MyPersonaPage activeJob={activeJob} onBuildPersona={() => setTab(TABS.BUILD_PERSONA)} />;
    }

    if (tab === TABS.COMMUNITY) {
      return <CommunityPage />;
    }

    if (tab === TABS.CONNECTIONS) {
      return <ConnectionsPage />;
    }

    if (tab === TABS.BUILD_PERSONA) {
      return (
        <UploadPage
          onJobCreated={setActiveJob}
          onJumpToViewer={() => setTab(TABS.MY_PERSONA)}
        />
      );
    }

    return <HomePage onNavigate={setTab} tabs={TABS} />;
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
          <button
            className={tab === TABS.MY_PERSONA ? "active" : ""}
            onClick={() => setTab(TABS.MY_PERSONA)}
          >
            My Persona
          </button>
          <button
            className={tab === TABS.COMMUNITY ? "active" : ""}
            onClick={() => setTab(TABS.COMMUNITY)}
          >
            Community
          </button>
          <button
            className={tab === TABS.CONNECTIONS ? "active" : ""}
            onClick={() => setTab(TABS.CONNECTIONS)}
          >
            Connections
          </button>
          <button
            className={tab === TABS.BUILD_PERSONA ? "active" : ""}
            onClick={() => setTab(TABS.BUILD_PERSONA)}
          >
            Build My Persona
          </button>
        </nav>
      </header>
      <main className="content">{content}</main>
    </div>
  );
}
