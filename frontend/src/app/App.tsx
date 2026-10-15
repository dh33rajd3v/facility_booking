import { Link, Navigate, Route, Routes } from "react-router-dom";
import { AppHeader } from "../components/AppHeader";
import { ApiStatus } from "../components/ApiStatus";
import { FacilityCatalogue } from "../features/facilities/FacilityCatalogue";

function NotFound() {
  return (
    <section className="page">
      <h1>Page not found</h1>
      <p>
        <Link to="/facilities">Go to the facility catalogue</Link>
      </p>
    </section>
  );
}

export function App() {
  return (
    <div className="layout">
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <AppHeader />
      <main id="main" className="layout__main">
        <Routes>
          {/* Week 1: the catalogue is the landing page. /home arrives with sign-in in Week 2. */}
          <Route path="/" element={<Navigate to="/facilities" replace />} />
          <Route path="/facilities" element={<FacilityCatalogue />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <footer className="app-footer">
        <span>Facilities Section, IIT Ropar</span>
        <ApiStatus />
      </footer>
    </div>
  );
}
