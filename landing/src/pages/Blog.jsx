import { Link } from "react-router-dom";
import { POSTS } from "../data/posts.js";

export default function Blog() {
  return (
    <section className="section">
      <div className="container">
        <header className="section__header">
          <h1 className="section__title">Blog</h1>
          <p className="section__subtitle">
            Notes on shipping data infrastructure.
          </p>
        </header>
        <div className="cards">
          {POSTS.map((post) => (
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
  );
}
