import { Link, useParams } from "react-router-dom";
import { POSTS_BY_SLUG } from "../data/posts.js";

export default function BlogPost() {
  const { slug } = useParams();
  const post = POSTS_BY_SLUG[slug];

  if (!post) {
    return (
      <section className="section">
        <div className="container">
          <h1>Post not found</h1>
          <p className="muted">
            The post you&rsquo;re looking for doesn&rsquo;t exist.
          </p>
          <p>
            <Link to="/blog">← Back to all posts</Link>
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="section">
      <div className="container" style={{ maxWidth: 760 }}>
        <p className="help-breadcrumbs">
          <Link to="/blog">Blog</Link> &nbsp;/&nbsp; {post.title}
        </p>
        <h1>{post.title}</h1>
        <p className="muted">{post.date}</p>
        <article
          className="help-content"
          style={{ marginTop: "1.5rem" }}
          dangerouslySetInnerHTML={{ __html: post.body }}
        />
      </div>
    </section>
  );
}
