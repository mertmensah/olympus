import { useEffect, useMemo, useState } from "react";
import HomePage from "./pages/HomePage";
import UploadPage from "./pages/UploadPage";
import MyPersonaPage from "./pages/MyPersonaPage";
import CommunityPage from "./pages/CommunityPage";
import ConnectionsPage from "./pages/ConnectionsPage";
import StyleGuidePage from "./pages/StyleGuidePage";
import { setAuthTokenGetter } from "./services/api";
import { getCurrentSession, signInWithEmail, signOutUser, signUpWithEmail, supabase } from "./supabase";

const TABS = {
  HOME: "home",
  MY_PERSONA: "my-persona",
  COMMUNITY: "community",
  CONNECTIONS: "connections",
  BUILD_PERSONA: "build-persona",
  STYLE_GUIDE: "style-guide"
};

export default function App() {
  const [tab, setTab] = useState(TABS.HOME);
  const [activeJob, setActiveJob] = useState(null);
  const [session, setSession] = useState(null);
  const [authReady, setAuthReady] = useState(false);
  const [authMode, setAuthMode] = useState("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState("");

  useEffect(() => {
    let isMounted = true;

    getCurrentSession()
      .then((nextSession) => {
        if (!isMounted) {
          return;
        }
        setSession(nextSession);
        setAuthTokenGetter(() => nextSession?.access_token || null);
        setAuthReady(true);
      })
      .catch(() => {
        if (!isMounted) {
          return;
        }
        setAuthReady(true);
      });

    const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      setAuthTokenGetter(() => nextSession?.access_token || null);
    });

    return () => {
      isMounted = false;
      data.subscription.unsubscribe();
    };
  }, []);

  async function handleAuthSubmit(event) {
    event.preventDefault();
    setAuthError("");
    try {
      if (authMode === "signin") {
        await signInWithEmail(email, password);
      } else {
        await signUpWithEmail(email, password);
      }
      setPassword("");
    } catch (error) {
      setAuthError(error.message || "Authentication failed");
    }
  }

  async function handleSignOut() {
    setAuthError("");
    await signOutUser();
    setTab(TABS.HOME);
  }

  const isAuthed = Boolean(session?.user?.id);
  const isProtectedTab = [TABS.MY_PERSONA, TABS.COMMUNITY, TABS.CONNECTIONS, TABS.BUILD_PERSONA].includes(tab);

  const content = useMemo(() => {
    if (!authReady) {
      return <section className="panel"><p>Loading session...</p></section>;
    }

    if (!isAuthed && isProtectedTab) {
      return (
        <section className="panel">
          <h2>Login Required</h2>
          <p>Sign in to access My Persona, Build My Persona, Community, and Connections.</p>
        </section>
      );
    }

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

    if (tab === TABS.STYLE_GUIDE) {
      return <StyleGuidePage />;
    }

    return <HomePage onNavigate={setTab} tabs={TABS} />;
  }, [tab, activeJob, authReady, isAuthed, isProtectedTab]);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-crest" aria-hidden="true" />
          <strong>Olympus</strong>
          <span>Summit of Digital Immortality</span>
        </div>
        <div className="auth-block">
          {isAuthed ? (
            <div className="auth-inline">
              <span className="muted">{session.user.email || session.user.id}</span>
              <button type="button" className="ghost" onClick={handleSignOut}>
                Sign Out
              </button>
            </div>
          ) : (
            <form className="auth-form" onSubmit={handleAuthSubmit}>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email"
                required
              />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                required
              />
              <button className="primary" type="submit">
                {authMode === "signin" ? "Sign In" : "Sign Up"}
              </button>
              <button
                className="ghost"
                type="button"
                onClick={() => setAuthMode((current) => (current === "signin" ? "signup" : "signin"))}
              >
                {authMode === "signin" ? "Need account?" : "Have account?"}
              </button>
            </form>
          )}
          {authError ? <p className="error">{authError}</p> : null}
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
          <button
            className={tab === TABS.STYLE_GUIDE ? "active" : ""}
            onClick={() => setTab(TABS.STYLE_GUIDE)}
          >
            Style Guide
          </button>
        </nav>
      </header>
      <main className="content">{content}</main>
    </div>
  );
}
