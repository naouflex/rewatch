// Add new entries here to publish blog posts. `body` is plain HTML.
export const POSTS = [
  {
    id: "hello-world",
    slug: "hello-world",
    title: "Hello, world",
    date: "2026-05-03",
    excerpt:
      "An intro to this little site — what it is, why it exists, and what's coming next.",
    body: `
      <p>Welcome! This site is a small companion to our self-hosted
      analytics platform. It serves two purposes:</p>
      <ol>
        <li>It's a <strong>landing page</strong> for the platform — a
          quick overview of the work, links to projects, and a place
          for announcements.</li>
        <li>It's the <strong>help center</strong> the app loads inside
          its in-app help drawer (the <em>?</em> icon in the sidebar).</li>
      </ol>
      <p>That second point matters: the help drawer used to point at an
      external site we couldn't change. Now we own the docs, so they
      can match the conventions and tweaks of <em>this</em>
      deployment.</p>
    `,
  },
  {
    id: "ml-worker",
    slug: "shipping-the-ml-worker",
    title: "Shipping the ML worker",
    date: "2026-04-12",
    excerpt:
      "How a dedicated RQ worker for training and prediction kept heavy jobs from blocking interactive queries.",
    body: `
      <p>We split out a dedicated <code>ml-worker</code> service in
      <code>compose.yaml</code> built from <code>Dockerfile.ml</code>.
      It only listens on the <code>training</code> and
      <code>predicting</code> RQ queues, so a runaway scikit-learn fit
      can never starve regular dashboards.</p>
      <p>The same image layers <code>libgomp1</code> and
      <code>libopenblas</code> on top of the standard worker image,
      which means we don't pay that storage cost for every container in
      the stack.</p>
    `,
  },
  {
    id: "indexers",
    slug: "indexers-the-shape-of-our-data",
    title: "Indexers: the shape of our data",
    date: "2026-03-21",
    excerpt:
      "A short note on the new Indexers surface and how it pairs with the Models tab.",
    body: `
      <p>Indexers describe the shape of a dataset and how it should be
      sliced before it's fed to a model. Like queries, they have
      favourites, owners and an archive — and like models, they have a
      dedicated route in the sidebar.</p>
      <p>Tag your indexers as you go. A small vocabulary makes the list
      browseable a year from now.</p>
    `,
  },
];

export const POSTS_BY_SLUG = POSTS.reduce((acc, post) => {
  acc[post.slug] = post;
  return acc;
}, {});
