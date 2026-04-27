import React from "react";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, message: "" };
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      message: error?.message || "Unexpected frontend runtime error",
    };
  }

  componentDidCatch(error, errorInfo) {
    // Surface detailed traces in dev tools while keeping UI usable.
    console.error("Olympus frontend runtime error", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <main style={{ padding: "24px", fontFamily: '"Aptos", "Segoe UI", sans-serif' }}>
          <section
            style={{
              maxWidth: 820,
              border: "1px solid #cde0f2",
              borderRadius: 16,
              background: "#fff",
              boxShadow: "0 8px 20px rgba(65,108,146,0.12)",
              padding: 20,
            }}
          >
            <p style={{ margin: 0, color: "#2e5f8f", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", fontSize: 12 }}>
              Frontend Error
            </p>
            <h1 style={{ marginTop: 10, marginBottom: 10, fontSize: 28 }}>Olympus could not render this screen</h1>
            <p style={{ margin: 0, color: "#3f6282" }}>
              {this.state.message}
            </p>
            <p style={{ marginTop: 12, marginBottom: 0, color: "#3f6282" }}>
              Check browser console for stack trace and verify frontend environment setup in
              <strong> frontend/.env</strong>.
            </p>
          </section>
        </main>
      );
    }

    return this.props.children;
  }
}
