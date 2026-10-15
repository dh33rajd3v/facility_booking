import { NavLink } from "react-router-dom";

export function AppHeader() {
  return (
    <header className="app-header">
      <div className="app-header__inner">
        <NavLink to="/" className="app-header__brand">
          <span className="app-header__mark" aria-hidden="true">
            IIT
          </span>
          <span>
            <span className="app-header__title">Facility Booking</span>
            <span className="app-header__subtitle">Indian Institute of Technology Ropar</span>
          </span>
        </NavLink>
        <nav aria-label="Main">
          <NavLink to="/facilities" className="app-header__link">
            Facilities
          </NavLink>
        </nav>
      </div>
    </header>
  );
}
