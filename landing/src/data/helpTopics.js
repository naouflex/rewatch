// The help URLs below mirror those produced by client/app/components/HelpTrigger.jsx
// in the Redash app. Each `path` is what comes after "/help" in the original
// redash.io URL — keeping them in sync means the in-app help drawer can simply
// point at this site instead of redash.io and every existing trigger keeps
// working.
//
// `body` may be either a string of HTML, or undefined to render the generic
// "Coming soon" placeholder with a link to the upstream redash.io article.

export const HELP_GROUPS = [
  {
    id: "intro",
    title: "Getting Started",
    topics: [
      {
        id: "getting-started",
        path: "/user-guide/getting-started",
        title: "Getting Started with Redash",
        summary:
          "Connect a data source, write your first query, and build a dashboard.",
        body: `
          <p>Welcome! This guide walks you through the three things you need to
          do before Redash becomes useful in your team:</p>
          <ol>
            <li>Connect a <strong>data source</strong> in <code>Settings → Data Sources</code>.</li>
            <li>Write a <strong>query</strong> against that data source from the <code>Queries → New Query</code> screen.</li>
            <li>Pin the result to a <strong>dashboard</strong> so colleagues can keep an eye on it.</li>
          </ol>
          <h3>1. Connect a data source</h3>
          <p>Pick the database type, paste the connection details and hit
          <em>Test connection</em>. Redash never stores result rows on disk
          unless you explicitly enable caching — only the SQL and the metadata
          needed to display the result.</p>
          <h3>2. Write your first query</h3>
          <p>Use the schema browser on the left to discover tables. The query
          editor supports auto-complete and parameterised queries. Hit
          <code>Ctrl/Cmd + Enter</code> to execute.</p>
          <h3>3. Build a dashboard</h3>
          <p>Open <em>Dashboards → New Dashboard</em>, drop in the visualisation
          you just created, drag-resize it, and share the URL with the team.</p>
        `,
      },
    ],
  },
  {
    id: "queries",
    title: "Queries",
    topics: [
      {
        id: "queries-overview",
        path: "/user-guide/querying",
        title: "Writing Queries",
        summary: "Editor shortcuts, scheduling, parameters and more.",
        body: `
          <p>The query editor is the heart of Redash. A few tips to get the
          most out of it:</p>
          <ul>
            <li><strong>Auto-complete</strong> works on table and column names once the schema has loaded.</li>
            <li><strong>Snippets</strong> let you save reusable SQL fragments — see <em>Settings → Query Snippets</em>.</li>
            <li><strong>Schedule</strong> queries to refresh on a fixed cadence; results power dashboards and alerts.</li>
            <li><strong>Tag</strong> your queries so they can be filtered from the Queries list.</li>
          </ul>
        `,
      },
      {
        id: "query-parameters",
        path: "/user-guide/querying/query-parameters",
        title: "Query Parameters & Value Source Options",
        summary:
          "Make queries reusable with text, number, date and dropdown parameters.",
        body: `
          <p>Wrap any value in <code>{{ }}</code> and Redash will turn it into a
          parameter. From the parameter settings you can pick the input type:
          text, number, date, date range, dropdown, query-based dropdown, or
          multi-select.</p>
          <h3 id="Value-Source-Options">Value Source Options</h3>
          <p>For dropdown parameters the values can come from:</p>
          <ul>
            <li><strong>Static list</strong> — a fixed list of values you type in.</li>
            <li><strong>Query-based</strong> — the rows returned by another saved query (<code>name</code> + <code>value</code> columns).</li>
          </ul>
          <p>Parameters always render to URL query string, so dashboard filters
          can be deep-linked and shared.</p>
        `,
      },
      {
        id: "writing-queries-permissions",
        path: "/user-guide/querying/writing-queries",
        title: "Managing Query Permissions",
        summary: "Control who can edit a query and who can only view it.",
        body: `
          <h3 id="Managing-Query-Permissions">Managing Query Permissions</h3>
          <p>By default, only the query owner and admins can edit a query.
          Open the query, click the <em>kebab menu → Manage Permissions</em>
          and grant edit access to specific users.</p>
          <p>Viewers always have read access if they have access to the
          underlying data source group — there is no per-query view ACL.</p>
        `,
      },
      {
        id: "favorites-tagging",
        path: "/user-guide/querying/favorites-tagging",
        title: "Favorites & Tagging",
        summary: "Star the things you use the most and tag the rest.",
        body: `
          <h3 id="Favorites">Favorites</h3>
          <p>Click the star next to any query, dashboard or alert to add it to
          your favorites. The home page always shows the most recently
          favorited items first.</p>
          <h3>Tagging</h3>
          <p>Tags work on both queries and dashboards. They're free-form, so
          establish a small tag vocabulary with your team (for example
          <code>finance</code>, <code>ops</code>, <code>experimental</code>).</p>
        `,
      },
      {
        id: "query-results-data-source",
        path: "/user-guide/querying/query-results-data-source",
        title: "Query Results Data Source",
        summary:
          "Use one query's output as the input to another with the special Query Results data source.",
        body: `
          <p>The Query Results data source exposes the output of any cached
          query as a SQLite-flavoured table named <code>query_&lt;id&gt;</code>.
          You can join across multiple sources, run aggregations, and post-
          process results — without round-tripping back to the original
          database.</p>
          <p>This is the cleanest way to combine, for example, sales data from
          BigQuery with a CRM export from Postgres in a single dashboard.</p>
        `,
      },
    ],
  },
  {
    id: "dashboards",
    title: "Dashboards",
    topics: [
      {
        id: "dashboards-overview",
        path: "/user-guide/dashboards",
        title: "Dashboards",
        summary: "Compose visualisations into shareable boards.",
        body: `
          <p>Dashboards are made of <strong>widgets</strong>. A widget is either
          a saved visualisation (chart, table, counter…) or a free-form text
          block. Use text blocks to give context and group widgets visually.</p>
          <p>Drag the bottom-right corner of any widget to resize. Toggle
          <em>Edit</em> mode to rearrange the layout.</p>
        `,
      },
      {
        id: "sharing-dashboards",
        path: "/user-guide/dashboards/sharing-dashboards",
        title: "Sharing & Embedding Dashboards",
        summary: "Public URLs, embeds and access control.",
        body: `
          <p>From a dashboard's <em>Share</em> menu you have three options:</p>
          <ul>
            <li><strong>Manage permissions</strong> — give other Redash users edit access.</li>
            <li><strong>Public URL</strong> — generate an unguessable URL that bypasses login. Disable it again at any time from the same menu.</li>
            <li><strong>Embed</strong> — copy an <code>&lt;iframe&gt;</code> snippet to embed the dashboard inside another tool such as Notion or your internal portal.</li>
          </ul>
          <p>Public URLs respect the dashboard refresh schedule, so embedded
          dashboards stay current without any user being logged in.</p>
        `,
      },
    ],
  },
  {
    id: "visualizations",
    title: "Visualizations",
    topics: [
      {
        id: "formatting-numbers",
        path: "/user-guide/visualizations/formatting-numbers",
        title: "Formatting Numbers",
        summary:
          "Use D3 / numeral.js format strings to control axis labels and values.",
        body: `
          <p>Most numeric visualisation options accept a
          <a href="https://github.com/d3/d3-format#locale_format" target="_blank" rel="noopener">D3 format string</a>.
          Some common examples:</p>
          <ul>
            <li><code>0,0</code> — group thousands (1,234,567)</li>
            <li><code>0.00%</code> — percentage with two decimals</li>
            <li><code>$0,0.00</code> — currency</li>
            <li><code>0.00a</code> — abbreviated (1.23k, 4.56m)</li>
          </ul>
        `,
      },
    ],
  },
  {
    id: "alerts",
    title: "Alerts",
    topics: [
      {
        id: "alerts-overview",
        path: "/user-guide/alerts",
        title: "Alerts",
        summary: "Get notified when a query result crosses a threshold.",
        body: `
          <p>Alerts watch a single column of a single query. When the column's
          value matches the configured condition, Redash fires the alert and
          sends notifications to the destinations you've subscribed.</p>
          <p>Destinations include Slack, PagerDuty, generic webhooks, email,
          Microsoft Teams, and more.</p>
        `,
      },
      {
        id: "alert-setup",
        path: "/user-guide/alerts/setting-up-an-alert",
        title: "Setting Up a New Alert",
        summary: "Step-by-step walkthrough of creating your first alert.",
        body: `
          <ol>
            <li>Open the query whose result you want to watch.</li>
            <li>From the kebab menu pick <em>New Alert</em>.</li>
            <li>Pick the column, the comparison and the threshold value.</li>
            <li>Pick a notification destination (you can configure these in
            <em>Settings → Alert Destinations</em>).</li>
            <li>Save. Redash now re-evaluates the alert every time the
            underlying query refreshes.</li>
          </ol>
        `,
      },
      {
        id: "custom-alert-notifications",
        path: "/user-guide/alerts/custom-alert-notifications",
        title: "Custom Alert Notification Templates",
        summary:
          "Use Jinja templates to format the subject and body of alert notifications.",
        body: `
          <p>Alert notifications support a Jinja-style template language with
          access to the alert, the query, and the row that triggered the alert.
          A typical Slack template might look like:</p>
          <pre><code>:rotating_light: <em>{{ ALERT_NAME }}</em>
{{ QUERY_NAME }} returned <strong>{{ VALUE }}</strong>
&lt;{{ QUERY_URL }}|Open the query&gt;</code></pre>
        `,
      },
    ],
  },
  {
    id: "users",
    title: "Users & Auth",
    topics: [
      {
        id: "authentication-options",
        path: "/user-guide/users/authentication-options",
        title: "Authentication Options",
        summary:
          "Built-in password auth, Google OAuth, SAML, LDAP, and remote-user.",
        body: `
          <p>Redash ships with several authentication backends:</p>
          <ul>
            <li><strong>Password auth</strong> — enabled by default, can be turned off.</li>
            <li><strong>Google OAuth</strong> — restrict to one or more domains.</li>
            <li><strong>SAML 2.0</strong> — for SSO with Okta, OneLogin, Azure AD, etc.</li>
            <li><strong>LDAP</strong> — bind against your directory server.</li>
            <li><strong>Remote user</strong> — trust an HTTP header set by an upstream proxy (use with care).</li>
          </ul>
          <p>Configure all of them under <em>Settings → General</em> or via
          environment variables.</p>
        `,
      },
    ],
  },
  {
    id: "data-sources",
    title: "Data Sources",
    topics: [
      {
        id: "ds-athena",
        path: "/data-sources/amazon-athena-setup",
        title: "Amazon Athena",
        summary: "Connect Redash to Amazon Athena.",
      },
      {
        id: "ds-bigquery",
        path: "/data-sources/bigquery-setup",
        title: "Google BigQuery",
        summary: "Use a service account to connect to BigQuery.",
      },
      {
        id: "ds-url",
        path: "/data-sources/querying-urls",
        title: "URL",
        summary: "Query JSON / CSV endpoints over HTTP.",
      },
      {
        id: "ds-mongodb",
        path: "/data-sources/mongodb-setup",
        title: "MongoDB",
        summary: "Run aggregation pipelines against MongoDB.",
      },
      {
        id: "ds-google-spreadsheets",
        path: "/data-sources/querying-a-google-spreadsheet",
        title: "Google Spreadsheets",
        summary: "Treat a Google Sheet as a data source.",
      },
      {
        id: "ds-google-analytics",
        path: "/data-sources/google-analytics-setup",
        title: "Google Analytics",
        summary: "Connect to GA via a service account.",
      },
      {
        id: "ds-axibase",
        path: "/data-sources/axibase-time-series-database",
        title: "Axibase Time Series Database",
        summary: "Query time-series data from Axibase.",
      },
    ],
  },
  {
    id: "admin",
    title: "Admin",
    topics: [
      {
        id: "admin-mail",
        path: "/open-source/setup",
        title: "Open-source Setup & Mail Configuration",
        summary:
          "Environment variables for the open-source distribution, including SMTP.",
        body: `
          <h3 id="Mail-Configuration">Mail Configuration</h3>
          <p>Outgoing mail (alerts, invites, password resets) is configured via
          these environment variables:</p>
          <ul>
            <li><code>REDASH_MAIL_SERVER</code></li>
            <li><code>REDASH_MAIL_PORT</code></li>
            <li><code>REDASH_MAIL_USE_TLS</code> / <code>REDASH_MAIL_USE_SSL</code></li>
            <li><code>REDASH_MAIL_USERNAME</code> / <code>REDASH_MAIL_PASSWORD</code></li>
            <li><code>REDASH_MAIL_DEFAULT_SENDER</code></li>
          </ul>
          <p>The dev compose stack ships a built-in <code>maildev</code>
          container so you can see outgoing mail at
          <a href="http://localhost:1080" target="_blank" rel="noopener">http://localhost:1080</a>.</p>
        `,
      },
      {
        id: "admin-usage-data",
        path: "/open-source/admin-guide/usage-data",
        title: "Anonymous Usage Data Sharing",
        summary:
          "What's collected when usage data sharing is on, and how to disable it.",
        body: `
          <p>When enabled, Redash periodically pings the maintainers with the
          number of users, queries, dashboards and data sources — never with
          query content or PII. Set
          <code>REDASH_DISABLE_USAGE_DATA</code> to <code>true</code> to opt
          out completely.</p>
        `,
      },
    ],
  },
];

export const HELP_TOPICS_BY_PATH = HELP_GROUPS.flatMap((g) => g.topics).reduce(
  (acc, topic) => {
    acc[topic.path] = topic;
    return acc;
  },
  {}
);

// Origin of the upstream documentation; we link back to it for topics that
// haven't been documented locally yet.
export const UPSTREAM_HELP_ORIGIN = "https://redash.io/help";
