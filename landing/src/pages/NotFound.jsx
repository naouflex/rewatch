import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <section className="section">
      <div className="container">
        <h1>404</h1>
        <p className="lead">We couldn&rsquo;t find that page.</p>
        <p>
          <Link to="/">← Back to home</Link>
        </p>
      </div>
    </section>
  );
}
