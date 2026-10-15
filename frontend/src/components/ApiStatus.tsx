import { useEffect, useState } from "react";
import { fetchHealth } from "../api/facilities";

type Status = "checking" | "ok" | "degraded" | "offline";

const TEXT: Record<Status, string> = {
  checking: "Checking server…",
  ok: "Server and database online",
  degraded: "Server online, database unreachable",
  offline: "Server unreachable",
};

export function ApiStatus() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    const controller = new AbortController();
    fetchHealth(controller.signal)
      .then((health) => setStatus(health.database === "ok" ? "ok" : "degraded"))
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        // /health returns 503 with a body when the DB is down; the API client throws for non-2xx.
        const code = (err as { status?: number }).status;
        setStatus(code === 503 ? "degraded" : "offline");
      });
    return () => controller.abort();
  }, []);

  return (
    <span className={`api-status api-status--${status}`}>
      <span className="api-status__dot" aria-hidden="true" />
      {TEXT[status]}
    </span>
  );
}
