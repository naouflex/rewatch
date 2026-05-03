# `landing/` — Companion site for the analytics platform

A small Vite + React app that serves two purposes:

1. **Landing page** — a public face for our self-hosted analytics
   platform with a featured-work section and a blog.
2. **Help center** — the in-app help drawer of the analytics app (the
   `?` icon in the sidebar) loads pages from this site.

## Layout

```
landing/
├── Dockerfile            # multi-stage build → nginx
├── nginx.conf            # SPA fallback + cache rules, no X-Frame-Options
├── package.json
├── vite.config.js
├── index.html
└── src/
    ├── main.jsx          # React entry, mounts <BrowserRouter>
    ├── App.jsx           # routes + embed-mode chrome toggle
    ├── components/       # Navbar, Footer, HelpSidebar, HelpLayout
    ├── data/             # helpTopics, posts, projects (edit these)
    ├── hooks/            # useIframeUrlBridge — postMessage to parent
    ├── pages/            # Home, Work, Blog, BlogPost, HelpHome, HelpPage
    └── styles/globals.css
```

## Adding content

* **Blog post** → push a new entry into `src/data/posts.js`.
* **Project** → push a new entry into `src/data/projects.js`.
* **Help article** → add an entry to the right group in
  `src/data/helpTopics.js`. The `path` field MUST mirror what
  `client/app/components/HelpTrigger.jsx` produces, so existing in-app
  question-mark icons land on the right page.

## Local development

```bash
cd landing
npm install
npm run dev          # http://localhost:5173
```

## Inside Docker Compose

The `landing` service in the repo's top-level `compose.yaml` builds
this folder and exposes it on `http://localhost:5002`. The host app's
`HelpTrigger` component is configured to load that URL inside the help
drawer (override with the `REDASH_HELP_BASE_URL` env var when building
the host frontend).

## In-iframe behaviour

When the page detects it is being rendered inside an iframe (or when
`?embed=1` is appended), the navbar and footer are hidden so the help
drawer feels native. On every navigation the page also posts a
`{ type: "iframe_url", message: <href> }` message to its parent so the
"open in new window" button in the drawer always points at the page
the user is actually looking at.
