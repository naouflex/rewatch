import { Link } from "react-router-dom";
import { PROJECTS } from "../data/projects.js";
import { POSTS } from "../data/posts.js";

export default function Home() {
  const recentPosts = POSTS.slice(0, 3);

  return (
    <>
      <section className="hero">
        <div className="container">
          <span className="hero__eyebrow">Companion site</span>
          <h1 className="hero__title">
            Analytics, models and the docs that make them usable.
          </h1>
          <p className="hero__lead">
            A small landing page for our self-hosted analytics platform.
            It also doubles as the in-app help center — every
            question-mark icon inside the app opens a page from this
            site.
          </p>
          <div className="hero__cta">
            <Link to="/help" className="btn btn--primary">
              Browse the help center →
            </Link>
            <Link to="/work" className="btn btn--ghost">
              See the work
            </Link>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <header className="section__header">
            <h2 className="section__title">Featured work</h2>
            <p className="section__subtitle">
              A snapshot of the things we&rsquo;re building around the
              tool.
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

      <section className="section">
        <div className="container">
          <header className="section__header">
            <h2 className="section__title">From the blog</h2>
            <p className="section__subtitle">
              Notes on shipping data infrastructure.
            </p>
          </header>
          <div className="cards">
            {recentPosts.map((post) => (
              <Link
                key={post.id}
                to={`/blog/${post.slug}`}
                className="card"
              >
                <span className="card__tag">{post.date}</span>
                <h3 className="card__title">{post.title}</h3>
                <p className="card__excerpt">{post.excerpt}</p>
                <div className="card__meta">
                  <span>Read post →</span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
