"use client";

/**
 * global-error replaces the root layout when a root-level render fails, so it
 * must ship its own <html>/<body> and inline styles (global CSS may not apply).
 */
export default function GlobalError({
  error,
  unstable_retry,
}: {
  error: Error & { digest?: string };
  unstable_retry: () => void;
}) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#010102",
          color: "#f7f8f8",
          fontFamily:
            "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
        }}
      >
        <div style={{ maxWidth: 420, padding: 24, textAlign: "center" }}>
          <h1 style={{ fontSize: 20, fontWeight: 600, margin: "0 0 8px" }}>
            Something went wrong
          </h1>
          <p style={{ fontSize: 14, lineHeight: 1.6, color: "#8a8f98", margin: 0 }}>
            RoundLab hit an unexpected error. Your saved work is unaffected. Try
            again, and if it keeps happening, reload the page.
          </p>
          {error.digest && (
            <p style={{ fontSize: 11, color: "#62666d", marginTop: 12 }}>
              Reference: {error.digest}
            </p>
          )}
          <button
            onClick={() => unstable_retry()}
            style={{
              marginTop: 24,
              padding: "8px 16px",
              fontSize: 14,
              fontWeight: 500,
              color: "#fff",
              background: "#5e6ad2",
              border: "none",
              borderRadius: 8,
              cursor: "pointer",
            }}
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
