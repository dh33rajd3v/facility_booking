import { Link } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { CATEGORY_LABELS } from "../../utils/format";

export function HomePage() {
  const { user } = useAuth();
  if (!user) return null;

  return (
    <section className="page" aria-labelledby="home-heading">
      <div className="page__intro">
        <h1 id="home-heading">Welcome, {user.name.split(" ")[0]}</h1>
        <p>
          Rate category: <strong>{user.rate_category ? CATEGORY_LABELS[user.rate_category] : "Not set"}</strong>
          {!user.is_iit && (
            <>
              {" "}
              · <Link to="/profile/category">Change</Link>
            </>
          )}
        </p>
      </div>

      <div className="home-cards">
        <Link to="/requests/new" className="home-card">
          <span className="home-card__title">Book a facility</span>
          <span className="home-card__text">
            Start a request for one event. Add lecture halls, the auditorium or sports grounds, each with its own date and
            slot.
          </span>
        </Link>
        <Link to="/requests" className="home-card">
          <span className="home-card__title">My requests</span>
          <span className="home-card__text">See your drafts and requests, and continue where you left off.</span>
        </Link>
        <Link to="/facilities" className="home-card home-card--plain">
          <span className="home-card__title">Facility catalogue</span>
          <span className="home-card__text">Capacities, slots and tariffs for every facility.</span>
        </Link>
      </div>
    </section>
  );
}
