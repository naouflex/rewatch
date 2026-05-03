import { Link } from "react-router-dom";
import { PROJECTS } from "../data/projects.js";

export default function Work() {
  return (
    <section className="section">
      <div className="container">
        <header className="section__header">
          <h1 className="section__title">Work</h1>
          <p className="section__subtitle">
            Selected projects we maintain around the analytics tool.
          </p>
        </header>
        <div className="cards">
          {PROJECTS.map((project) => (
            <Link key={project.id} to={project.href} className="card">
              <span className="card__tag">{project.tag}</span>
              <h3 className="card__title">{project.title}</h3>
              <p className="card__excerpt">{project.excerpt}</p>
              <div className="card__meta">
                <span>Read more →</span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
