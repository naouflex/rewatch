// Help articles served by this site. Each `path` is the URL fragment that
// comes after "/help" — keeping the paths stable means the in-app help
// drawer (the `?` icon in the sidebar) can deep-link to any topic.
//
// `body` holds the rendered HTML for the article. Topics without a body
// fall back to a friendly "documentation coming soon" placeholder.

export const HELP_GROUPS = [
  {
    id: "intro",
    title: "Getting Started",
    topics: [
      {
        id: "getting-started",
        path: "/user-guide/getting-started",
        title: "Getting Started",
        summary:
          "Connect a data source, write your first query, build a dashboard, and invite your team.",
        body: `
          <h2>1. Add a data source</h2>
          <p>The first thing you'll want to do is connect a data source.
          Open the data source management page by clicking the
          <em>Settings</em> icon in the sidebar, then pick the database
          type from the catalogue (Postgres, MySQL, BigQuery, MongoDB,
          and dozens more).</p>
          <p>If your database lives behind a firewall, allow inbound
          access from the host running the app. We recommend using a
          dedicated user with read-only permissions wherever possible.</p>

          <h2>2. Write a query</h2>
          <p>Once a data source is connected, click <em>Create</em> in
          the navigation bar and pick <em>Query</em>. The editor speaks
          the query language native to the underlying data source —
          usually SQL, but JSON / Mongo aggregation pipelines for
          document stores. See
          <a href="/help/user-guide/querying/writing-queries">Creating
          and Editing Queries</a> for keyboard shortcuts and the schema
          browser tour.</p>

          <h2>3. Add visualizations</h2>
          <p>By default, query results appear as a table. Visualizations
          help you see patterns at a glance: click <em>New Visualization</em>
          above the results pane to pick a chart type. Most chart types
          (line, bar, area, pie, funnel, sankey, choropleth maps and
          more) are available out of the box.</p>

          <h2>4. Create a dashboard</h2>
          <p>Combine visualizations and free-form text into thematic
          dashboards. Click <em>Create</em> in the navigation bar and
          choose <em>Dashboard</em>. Dashboards are visible to your team
          members and can also be shared via secret link with people
          outside your organization. See
          <a href="/help/user-guide/dashboards">Dashboards</a> for the
          full walkthrough.</p>

          <h2>5. Invite colleagues</h2>
          <p>Analytics is better as a team sport. To invite a new user,
          go to <em>Settings → Users</em> and click <em>New User</em>;
          they'll receive an email invite and be prompted to set a
          password (or sign in via SSO if you've configured it).</p>
          <p>To add a user to an existing group, open
          <em>Settings → Groups</em>, pick a group, and start typing the
          user's name in the member field.</p>
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
        title: "Querying",
        summary:
          "An index of every querying topic — editor, parameters, scheduling, snippets, and exports.",
        body: `
          <p>The query editor is the heart of the tool. The pages in
          this group cover every aspect of writing, running and sharing
          queries:</p>
          <ul>
            <li><a href="/help/user-guide/querying/writing-queries">Creating and editing queries</a> — editor shortcuts, schema browser, auto-complete and the publish/archive workflow.</li>
            <li><a href="/help/user-guide/querying/query-results-data-source">Querying existing query results</a> — join across data sources by treating other queries as tables.</li>
            <li><a href="/help/user-guide/querying/query-parameters">Query parameters</a> — make queries reusable with text, number, date, dropdown and query-based parameters.</li>
            <li><a href="/help/user-guide/querying/favorites-tagging">Favorites &amp; tagging</a> — keep your most-used queries within reach.</li>
          </ul>
        `,
      },
      {
        id: "writing-queries",
        path: "/user-guide/querying/writing-queries",
        title: "Creating and Editing Queries",
        summary:
          "Editor shortcuts, schema browser, auto-complete, publishing, archiving and forking.",
        body: `
          <p>To create a new query, click <em>Create</em> in the navbar
          and choose <em>Query</em>.</p>

          <h2>The query editor</h2>

          <h3>Query syntax</h3>
          <p>In most cases the query language is the one native to the
          data source. Where the tool layers something on top — for
          example its YAML syntax for HTTP / JSON sources or extended
          MongoDB JSON — that's documented on the per-source pages.</p>

          <h3>Keyboard shortcuts</h3>
          <ul>
            <li>Execute query: <code>Ctrl</code>/<code>Cmd</code> + <code>Enter</code></li>
            <li>Save query: <code>Ctrl</code>/<code>Cmd</code> + <code>S</code></li>
            <li>Toggle auto-complete: <code>Ctrl</code> + <code>Space</code></li>
            <li>Toggle schema browser: <code>Alt</code>/<code>Option</code> + <code>D</code></li>
          </ul>

          <h3>Schema browser</h3>
          <p>The pane on the left lists every table the connected data
          source exposes. Click a table to expand its columns; click the
          double-arrow icon to insert the identifier into your query.
          The search box filters the schema, and the refresh button
          forces a re-fetch (otherwise it refreshes periodically in the
          background).</p>
          <p>Not every data source can introspect its schema — that's
          fine, the schema browser will simply stay empty.</p>

          <h3>Auto-complete</h3>
          <p>Live auto-complete is on by default and suggests tables,
          columns and SQL keywords as you type. Disable it with the
          lightning-bolt icon below the editor; you can still trigger a
          single completion with <code>Ctrl</code> + <code>Space</code>.</p>
          <p>For schemas larger than five thousand identifiers, live
          auto-complete is automatically off to keep the editor snappy.
          Auto-complete also recognises any saved
          <a href="/help/user-guide/querying">query snippets</a>.</p>

          <h2>Query settings</h2>

          <h3>Published vs unpublished queries</h3>
          <p>Each query starts as an unpublished draft and is invisible
          to dashboards and alerts. Renaming the query or clicking
          <em>Publish</em> publishes it; clicking <em>Unpublish</em>
          reverses the action (existing dashboards and alerts that already
          reference the query keep working — only new ones are blocked).</p>
          <p>Publishing does not change visibility: every signed-in user
          in the organization can see every query.</p>

          <h3>Archiving a query</h3>
          <p>You can't delete queries — but you can archive them.
          Archiving hides the query from the lists while keeping
          permalinks alive. Open the kebab menu (<code>⋮</code>) at the
          top right and pick <em>Archive</em>.</p>

          <h3>Duplicating (forking) a query</h3>
          <p>Need a copy of an existing query, whether yours or
          someone else's? Hit the <em>Fork</em> button. You become the
          owner of the new copy.</p>

          <h2 id="Managing-Query-Permissions">Managing query permissions</h2>
          <p>By default, only the query owner and members of the
          <em>Admin</em> group can edit a saved query. Experimental
          multi-owner support lets you share edit access with anyone
          else: an admin needs to enable
          <em>Settings → Organization → Enable experimental multiple
          owners support</em> first.</p>
          <p>Once enabled, the kebab menu on every query gains a
          <em>Manage Permissions</em> entry. Use the dialog that opens
          to add other users as editors. Note that they will <em>not</em>
          receive an automatic notification, so you'll want to ping them
          yourself.</p>
        `,
      },
      {
        id: "query-parameters",
        path: "/user-guide/querying/query-parameters",
        title: "Query Parameters",
        summary:
          "Make queries reusable with text, number, date, dropdown and query-based parameters.",
        body: `
          <p>Parameters let you substitute values into a query at run
          time without touching the source. Wrap any identifier in
          double curly braces — <code>{{ }}</code> — and a widget will
          appear above the results pane to set its value.</p>
          <p>While editing, click the gear icon next to a parameter
          widget to adjust its settings. The gear icons disappear in
          read-only mode so non-owners can't change the parameter
          configuration.</p>

          <h2>Adding a parameter from the UI</h2>
          <p>The <em>Add Parameter</em> button (and its keyboard
          shortcut, shown when you hover the button) inserts a parameter
          at the cursor position and immediately opens its settings
          panel.</p>

          <h3>Parameter settings</h3>
          <ul>
            <li><strong>Title</strong> — the display name above the input. Defaults to the keyword inside <code>{{ }}</code>.</li>
            <li><strong>Type</strong> — Text, Number, Date, Date and Time, Date and Time (with seconds), Date Range, or Dropdown List.</li>
          </ul>
          <p>For security reasons, only users with <em>Full Access</em>
          on the data source can use Text-typed parameters (they are
          not safe from SQL injection). Date, Number and Dropdown
          parameters can be used by anyone who can see the query.</p>

          <h3>Date and date-range parameters</h3>
          <p>Date pickers can default to the current date / time and
          come in three precisions: Date, Date and Time, and Date and
          Time with seconds.</p>
          <p>A date-range parameter exposes two markers — <code>.start</code>
          and <code>.end</code> — that you reference in the query:</p>
          <pre><code>SELECT a, b, c
FROM table1
WHERE
  relevant_date &gt;= '{{ myDate.start }}'
  AND relevant_date &lt;= '{{ myDate.end }}'</code></pre>
          <p>Date parameters are passed as strings, so wrap them in
          single quotes (or whatever your database uses for string
          literals).</p>

          <h4>Quick date and date-range options</h4>
          <p>The lightning-bolt glyph next to a date widget exposes
          dynamic shortcuts such as "Today", "Yesterday" or
          "Last 30 days". The full set of dynamic ranges is:</p>
          <ul>
            <li>This week / month / year</li>
            <li>Last week / month / year</li>
            <li>Last 7 / 14 / 30 / 60 / 90 days</li>
            <li>Last 12 months</li>
          </ul>
          <p>Because dynamic dates are computed in the browser, they
          can't be used inside scheduled queries.</p>

          <h3>Dropdown lists</h3>
          <p>Use the Dropdown List type to restrict the values a user
          can pass to a query. Enter the allowed values one per line in
          the settings panel — under the hood they're plain text
          parameters, so date / datetime values must already be in the
          format your data source expects.</p>

          <h4>Query-based dropdown lists</h4>
          <p>Dropdowns can also be populated from the result of another
          saved query. Pick <em>Query Based Dropdown List</em>, then
          choose the source query.</p>
          <p>If the source query returns just one column, that column
          drives both the displayed label and the substituted value.
          When it returns <code>name</code> and <code>value</code>
          columns, the widget shows <code>name</code> values and
          substitutes <code>value</code>:</p>
          <pre><code>SELECT user_uuid AS value, username AS name
FROM users</code></pre>
          <p>Performance degrades for very large result sets — keep
          dropdown queries under a few thousand rows.</p>

          <h4>Multi-select dropdowns</h4>
          <p>Toggle <em>Allow multiple values</em> to let users pick
          several options. Choose whether to wrap values in single or
          double quotes, then write your query with <code>IN</code>:</p>
          <pre><code>SELECT ...
FROM   ...
WHERE field IN ( {{ Multi Select Parameter }} )</code></pre>

          <h3>FAQ</h3>
          <p><strong>Can I reuse the same parameter multiple times in a
          single query?</strong> Yes — just use the same identifier in
          each <code>{{ }}</code> instance.</p>
          <p><strong>Can I use multiple parameters in a single query?</strong>
          Yes; give each one a unique name.</p>
          <p><strong>Can parameters be used in embedded visualizations
          and shared dashboards?</strong> All parameter types <em>except
          Text</em> can be used safely in public embeds. Text parameters
          are blocked because they are not safe from SQL injection.</p>
          <p><strong>Can I change a parameter value via the URL?</strong>
          Yes. Each parameter is exposed in the query string prefixed
          with <code>p_</code>, e.g.
          <code>/queries/1234?p_param=100</code>. Useful for cross-linking
          between queries and dashboards.</p>

          <h2 id="Value-Source-Options">Parameter mapping on dashboards</h2>
          <p>When a dashboard widget depends on a parameterised query,
          the parameter mapping dialog (under the widget's kebab menu)
          lets you decide where each parameter's value comes from:</p>
          <ul>
            <li><strong>New dashboard parameter</strong> — create a single
            value selector at the top of the dashboard and reuse it
            across multiple widgets.</li>
            <li><strong>Existing dashboard parameter</strong> — bind this
            widget's parameter to a previously-created dashboard
            parameter.</li>
            <li><strong>Widget parameter</strong> — show a value selector
            inside this single widget; useful for one-off filters.</li>
            <li><strong>Static value</strong> — hard-code a value for this
            widget. The selector is hidden, which keeps the dashboard
            tidy when a value is rarely going to change.</li>
          </ul>
          <p>The mapping dialog also exposes the keyword (the literal
          string between the curly braces) and the default value, useful
          for debugging when a dashboard returns unexpected results.</p>
        `,
      },
      {
        id: "favorites-tagging",
        path: "/user-guide/querying/favorites-tagging",
        title: "Favorites & Tagging",
        summary: "Star the things you use the most and tag the rest.",
        body: `
          <p>As your collection of queries and dashboards grows from a
          few hundred to a few thousand, favorites and tags are how you
          stay organised.</p>

          <h2 id="Favorites">Favorites</h2>
          <p>Click the star icon next to any dashboard or query title to
          favorite it. The star turns yellow to confirm. Favorites
          appear in three places:</p>
          <ul>
            <li>The home page, as a "Favorites" panel.</li>
            <li>The navbar dropdowns for Queries and Dashboards.</li>
            <li>As a filter on the query and dashboard list pages.</li>
          </ul>

          <h2>Tagging</h2>
          <p>You can tag both queries and dashboards. Hover over the
          title and click the <em>+ Add Tag</em> button that appears.
          The dialog suggests previously-used tags as you type — pick as
          many as you need and save. Press <kbd>Esc</kbd> to abort.</p>
          <p>A small, predictable tag vocabulary makes a big difference
          to onboarding new teammates. Agree on a flat set of common
          tags up front (<code>finance</code>, <code>ops</code>,
          <code>experimental</code>…) before letting tags grow
          organically.</p>
          <p>On the list pages, tags appear in the right-hand rail.
          Click a tag to filter the list; click again to clear.
          <kbd>Shift</kbd>-click to combine tags.</p>
        `,
      },
      {
        id: "query-results-data-source",
        path: "/user-guide/querying/query-results-data-source",
        title: "Querying Existing Query Results",
        summary:
          "Join data from multiple databases by treating other queries as tables.",
        body: `
          <p>The Query Results data source (QRDS) lets you run SQL
          against the cached results of any other query. It's powered
          by an in-memory SQLite database, so very large result sets can
          run out of memory — keep input queries reasonably sized.</p>

          <h2>Setup</h2>
          <p>Create a new data source under
          <em>Settings → Data Sources</em>, pick <em>Query Results</em>
          as the type and give it a name (most teams only need one).
          That name appears as a regular entry in the data source
          dropdown of the query editor.</p>

          <h2>Querying</h2>
          <p>Use SQLite syntax. Each upstream query is exposed as a
          table named <code>query_&lt;id&gt;</code>, where <code>id</code>
          is the numeric ID from the URL of the source query (e.g.
          <code>/queries/49588</code> → <code>query_49588</code>):</p>
          <pre><code>SELECT
  a.name,
  b.count
FROM query_123 AS a
JOIN query_456 AS b
  ON a.id = b.id</code></pre>
          <p>The <code>query_&lt;id&gt;</code> alias must appear on the
          same line as its associated <code>FROM</code> /
          <code>JOIN</code> keyword.</p>

          <h2>Cached query results</h2>
          <p>By default, executing a QRDS query also re-runs the source
          queries to get fresh data. To re-use the cached result of a
          source query (faster but possibly stale), prefix the alias
          with <code>cached_</code>:</p>
          <pre><code>FROM cached_query_123 AS a
JOIN query_456 AS b
  ON a.id = b.id</code></pre>
          <p>The two prefixes can be mixed in a single query.</p>

          <h2>Permissions</h2>
          <p>Access to the QRDS data source is governed by group
          membership like any other data source — but a user also needs
          permission on the original data source backing each referenced
          query, or they will only see the most recently cached result
          and won't be able to re-execute.</p>

          <h2>Using query parameters</h2>
          <p>You can pass parameters into a parameterised source query
          using the syntax <code>param_query_&lt;id&gt;_{key=value}</code>.
          For example, given a source query <code>123</code> that takes
          an <code>id</code> parameter:</p>
          <pre><code>SELECT a.name
FROM param_query_123_{id=1} AS a</code></pre>
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
        title: "Creating and Editing Dashboards",
        summary:
          "Combine visualizations and text into a single shareable view.",
        body: `
          <h2>Creating a dashboard</h2>
          <p>A dashboard combines visualizations and text boxes (for
          context). Use the <em>Create</em> menu in the navbar and pick
          <em>Dashboard</em>. After naming it, hit <em>Add Widget</em>
          to drop in an existing visualization or a text block. The
          widget picker lets you search published queries or pick from a
          recents list.</p>

          <h2>Dashboard URLs</h2>
          <p>Each dashboard gets an <code>id</code> and a
          <code>slug</code> derived from its name. For example, a
          dashboard called "Account Overview" might live at:</p>
          <pre><code>/dashboards/251-account-overview</code></pre>
          <p>If you rename the dashboard the slug updates automatically.
          The singular <code>/dashboard/&lt;id-or-slug&gt;</code>
          endpoint also works:</p>
          <pre><code>/dashboard/251
/dashboard/account-overview</code></pre>
          <p>IDs are unique. If multiple dashboards share the same slug,
          visiting the slug URL redirects to the earliest-created one.</p>

          <h2>Picking visualizations</h2>
          <p>Widgets pick from existing query visualizations. You can't
          create a brand-new visualization from inside the
          <em>Add Widget</em> dialog — open the underlying query and add
          the visualization there first.</p>

          <h2>Adding text boxes</h2>
          <p>The <em>Text Box</em> tab in the <em>Add Widget</em> dialog
          accepts <a href="https://daringfireball.net/projects/markdown/syntax" target="_blank" rel="noopener">Markdown</a>,
          including inline images via the standard
          <code>![alt](url)</code> syntax. Use text boxes liberally to
          explain what each section of the dashboard represents.</p>

          <h2>Dashboard filters</h2>
          <p>If your queries use filters, enable
          <em>Use Dashboard Level Filters</em> from
          <em>Dashboard Settings</em> to apply the same filter across
          every widget at once.</p>

          <h2>Managing dashboard permissions</h2>
          <p>By default, only the dashboard owner and admins can edit a
          dashboard. Experimental multi-owner support lets you share
          edit access — an admin needs to flip
          <em>Settings → Organization → Enable experimental multiple
          owners support</em> first. Once enabled, the dashboard's
          options menu gains a <em>Manage Permissions</em> entry where
          you can add other editors. As with queries, no notification
          is sent automatically.</p>

          <h2>Refreshing</h2>
          <p>Even large dashboards load quickly because every widget
          reads from a query result cache. To force a manual refresh,
          click the <em>Refresh</em> button at the top right; this
          re-runs every query on the dashboard.</p>
          <p>To refresh on a schedule, open the refresh dropdown and
          pick an interval. Allowed intervals (in seconds): 60, 300,
          600, 1800, 3600, 43200, 86400. You can also pass
          <code>?refresh=&lt;seconds&gt;</code> in the URL.</p>
          <p>Automatic refresh runs in the browser, so it only ticks
          while a logged-in user has the dashboard open. To guarantee
          fresh data for alerts and embeds, schedule the underlying
          queries instead.</p>
        `,
      },
      {
        id: "sharing-dashboards",
        path: "/user-guide/dashboards/sharing-dashboards",
        title: "Sharing and Embedding Dashboards",
        summary:
          "Publish, share via secret link, and embed dashboards in other tools.",
        body: `
          <p>Click the <em>Publish</em> button in the top right of a
          dashboard to make it visible to other signed-in members of the
          organization who have the right data source permissions.</p>
          <p>To share with people outside the organization, click the
          share icon next to <em>Publish</em>. The dialog generates a
          secret URL anyone with the link can open. External viewers see
          the dashboard widgets but cannot navigate the rest of the app
          or open the underlying queries.</p>
          <p>To revoke access, toggle <em>Allow public access</em> off.
          That breaks any previously-shared link; toggling it back on
          generates a fresh secret URL.</p>
          <p>Admins can globally disable all public URLs by setting the
          environment variable <code>REDASH_DISABLE_PUBLIC_URLS</code>
          to <code>"true"</code> on the server.</p>

          <h2>Permissions on shared dashboards</h2>
          <p>A signed-in viewer can only see widgets backed by data
          sources they have access to. Anyone who can see a widget can
          also open the underlying query. To share a dashboard while
          restricting query access, you have two options:</p>
          <ol>
            <li>Use the secret-link option — external viewers can't
            navigate to the underlying queries.</li>
            <li>Create a dedicated, narrowly-scoped data source for the
            restricted users and rely on database-level permissions.</li>
          </ol>

          <h2>Embedding dashboards</h2>
          <p>Some teams embed dashboards inside other tools (Notion,
          their internal portal, a wiki…) using <code>&lt;iframe&gt;</code>
          tags. To make embedding nicer, use the <em>Full Screen</em>
          button next to <em>Refresh</em>: it strips the chrome and gives
          you a clean URL to drop in your iframe. Note that embedding a
          private dashboard requires the viewer to be signed in; for
          external viewers, generate a secret link instead — secret
          links are full-screen by default.</p>
          <p>Embedded dashboards may use parameters, but any viewer can
          modify them. That makes the tool a poor fit for fully external
          embedded analytics — only share dashboards with stakeholders
          you trust.</p>
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
        title: "Formatting Numbers in Visualizations",
        summary:
          "Use numeral.js format strings to control how numbers are displayed.",
        body: `
          <p>Several visualizations let you control how numbers are
          formatted via a format string (the same format strings used by
          <a href="http://numeraljs.com/" target="_blank" rel="noopener">numeral.js</a>).
          Below is a quick reference for the most common cases.</p>

          <h2>Numbers</h2>
          <table>
            <thead><tr><th>Number</th><th>Format</th><th>Output</th></tr></thead>
            <tbody>
              <tr><td>10000</td><td><code>0,0.0000</code></td><td>10,000.0000</td></tr>
              <tr><td>10000.23</td><td><code>0,0</code></td><td>10,000</td></tr>
              <tr><td>10000.23</td><td><code>+0,0</code></td><td>+10,000</td></tr>
              <tr><td>-10000</td><td><code>0,0.0</code></td><td>-10,000.0</td></tr>
              <tr><td>10000.1234</td><td><code>0.000</code></td><td>10000.123</td></tr>
              <tr><td>100.1234</td><td><code>00000</code></td><td>00100</td></tr>
              <tr><td>10</td><td><code>000.00</code></td><td>010.00</td></tr>
              <tr><td>10000.1234</td><td><code>0[.]00000</code></td><td>10000.12340</td></tr>
              <tr><td>-10000</td><td><code>(0,0.0000)</code></td><td>(10,000.0000)</td></tr>
              <tr><td>1230974</td><td><code>0.0a</code></td><td>1.2m</td></tr>
              <tr><td>1460</td><td><code>0 a</code></td><td>1 k</td></tr>
              <tr><td>1</td><td><code>0o</code></td><td>1st</td></tr>
              <tr><td>100</td><td><code>0o</code></td><td>100th</td></tr>
            </tbody>
          </table>

          <h2>Currency</h2>
          <table>
            <thead><tr><th>Number</th><th>Format</th><th>Output</th></tr></thead>
            <tbody>
              <tr><td>1000.234</td><td><code>$0,0.00</code></td><td>$1,000.23</td></tr>
              <tr><td>1000.2</td><td><code>0,0[.]00 $</code></td><td>1,000.20 $</td></tr>
              <tr><td>1001</td><td><code>$ 0,0[.]00</code></td><td>$ 1,001</td></tr>
              <tr><td>-1000.234</td><td><code>($0,0)</code></td><td>($1,000)</td></tr>
              <tr><td>1230974</td><td><code>($ 0.00 a)</code></td><td>$ 1.23 m</td></tr>
            </tbody>
          </table>

          <h2>Bytes</h2>
          <table>
            <thead><tr><th>Number</th><th>Format</th><th>Output</th></tr></thead>
            <tbody>
              <tr><td>100</td><td><code>0b</code></td><td>100B</td></tr>
              <tr><td>1024</td><td><code>0b</code></td><td>1KB</td></tr>
              <tr><td>2048</td><td><code>0 ib</code></td><td>2 KiB</td></tr>
              <tr><td>3072</td><td><code>0.0 b</code></td><td>3.1 KB</td></tr>
              <tr><td>7884486213</td><td><code>0.00b</code></td><td>7.88GB</td></tr>
            </tbody>
          </table>

          <h2>Percentages</h2>
          <table>
            <thead><tr><th>Number</th><th>Format</th><th>Output</th></tr></thead>
            <tbody>
              <tr><td>100</td><td><code>0%</code></td><td>100%</td></tr>
              <tr><td>97.4878234</td><td><code>0.000%</code></td><td>97.488%</td></tr>
              <tr><td>-4.3</td><td><code>0 %</code></td><td>-4 %</td></tr>
              <tr><td>65.43</td><td><code>(0.000 %)</code></td><td>65.430 %</td></tr>
            </tbody>
          </table>

          <h2>Exponential</h2>
          <table>
            <thead><tr><th>Number</th><th>Format</th><th>Output</th></tr></thead>
            <tbody>
              <tr><td>1123456789</td><td><code>0,0e+0</code></td><td>1e+9</td></tr>
              <tr><td>12398734.202</td><td><code>0.00e+0</code></td><td>1.24e+7</td></tr>
              <tr><td>0.000123987</td><td><code>0.000e+0</code></td><td>1.240e-4</td></tr>
            </tbody>
          </table>
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
        summary:
          "Get notified when a query result crosses a threshold you care about.",
        body: `
          <p>Alerts watch a single column of a single (parameter-free)
          query and fire a notification when its value crosses a
          threshold. The pages in this group cover alerts end-to-end:</p>
          <ul>
            <li><a href="/help/user-guide/alerts/setting-up-an-alert">Setting up an alert</a> — pick a query, a value column, a condition and a threshold.</li>
            <li><a href="/help/user-guide/alerts/custom-alert-notifications">Customising alert notifications</a> — write your own subject and body templates with variables.</li>
          </ul>
          <p>Alerts are evaluated after every execution of the
          underlying query, so you'll typically pair them with a
          schedule. Alerts cannot be attached to parameterised queries.</p>
        `,
      },
      {
        id: "alert-setup",
        path: "/user-guide/alerts/setting-up-an-alert",
        title: "Setting Up an Alert",
        summary: "Step-by-step walkthrough of creating your first alert.",
        body: `
          <p>Alerts notify you when a field returned by a
          <a href="/help/user-guide/querying">scheduled query</a> meets
          a threshold. They're great for monitoring the health of your
          business and for kicking off downstream workflows in tools
          like Zapier or IFTTT.</p>
          <p>A query schedule is not strictly required, but it is
          strongly recommended. If you attach an alert to a non-scheduled
          query, you'll only be notified when someone runs that query
          manually.</p>
          <p>Alerts <em>do not</em> work for queries that take parameters.</p>

          <h2>The alerts list</h2>
          <p>Click <em>Alerts</em> in the navbar to see every alert, by
          default sorted reverse-chronologically by creation date.
          Re-sort by clicking any column header.</p>
          <ul>
            <li><strong>Name</strong> — the alert's display name. You can rename it any time.</li>
            <li><strong>Created By</strong> — the user who created it.</li>
            <li><strong>State</strong> — <code>UNKNOWN</code>, <code>TRIGGERED</code> or <code>OK</code>.</li>
          </ul>

          <h2>Creating an alert</h2>
          <ol>
            <li>Click <em>Create</em> in the navbar, then <em>New Alert</em>.</li>
            <li>Search for a target query. If you don't see it, make sure it's published and uses no parameters.</li>
            <li>Configure the trigger:
              <ul>
                <li><strong>Value column</strong> — which field of the result is evaluated.</li>
                <li><strong>Condition</strong> — the comparison operator.</li>
                <li><strong>Threshold</strong> — the value the column is compared against.</li>
              </ul>
              If the query returns multiple rows, only the first one is used. The current value of the chosen column shows up beneath the dropdown.
            </li>
            <li>Pick how often to be notified while the alert remains <code>TRIGGERED</code>:
              <ul>
                <li><em>Just once</em> — notify once when the status flips from <code>OK</code> to <code>TRIGGERED</code>.</li>
                <li><em>Each time alert is evaluated</em> — notify on every evaluation while triggered.</li>
                <li><em>At most every</em> — set a minimum interval between notifications.</li>
              </ul>
              Regardless of which option you pick, you'll always get a notification when the status crosses from <code>OK</code> to <code>TRIGGERED</code> or back.
            </li>
            <li>Pick a <strong>template</strong>. The default template links to the alert and query screens; for richer messages see <a href="/help/user-guide/alerts/custom-alert-notifications">Customising alert notifications</a>.</li>
            <li>Click <em>Create Alert</em> and then choose at least one destination — without a destination you won't receive anything.</li>
          </ol>

          <h2>Muting alerts</h2>
          <p>To temporarily silence an alert without deleting it, open
          its kebab menu (<code>⋮</code>) and pick
          <em>Mute Notifications</em>. Use the same menu to unmute.</p>

          <h2 id="Alert-Status-&-Frequency">Alert statuses</h2>
          <ul>
            <li><strong><code>TRIGGERED</code></strong> — the value column matched the configured condition on the most recent run.</li>
            <li><strong><code>OK</code></strong> — the most recent run did not match the condition. (The alert may have been triggered before — this only describes the latest run.)</li>
            <li><strong><code>UNKNOWN</code></strong> — there isn't enough data to evaluate the alert: shown immediately after creation, or when the query result is empty / missing the value column.</li>
          </ul>

          <h2 id="Configuration-settings">Notification frequency in practice</h2>
          <p>Notifications fire whenever the alert status changes from
          <code>OK</code> to <code>TRIGGERED</code> or vice versa.
          Consider an alert on a query that runs daily; suppose its
          status across the week is:</p>
          <table>
            <thead><tr><th>Day</th><th>Status</th></tr></thead>
            <tbody>
              <tr><td>Monday</td><td><code>OK</code></td></tr>
              <tr><td>Tuesday</td><td><code>OK</code></td></tr>
              <tr><td>Wednesday</td><td><code>TRIGGERED</code></td></tr>
              <tr><td>Thursday</td><td><code>TRIGGERED</code></td></tr>
              <tr><td>Friday</td><td><code>TRIGGERED</code></td></tr>
              <tr><td>Saturday</td><td><code>TRIGGERED</code></td></tr>
              <tr><td>Sunday</td><td><code>OK</code></td></tr>
            </tbody>
          </table>
          <p>With the frequency set to <em>Just once</em>, you'd be
          notified on Wednesday (status flipped to triggered) and on
          Sunday (back to OK). Choose <em>Each time alert is evaluated</em>
          to also be notified on Thursday, Friday and Saturday.</p>
        `,
      },
      {
        id: "custom-alert-notifications",
        path: "/user-guide/alerts/custom-alert-notifications",
        title: "Customising Alert Notifications",
        summary:
          "Override the default subject and body templates with built-in template variables.",
        body: `
          <p>The default alert templates link to the alert and query
          screens, which is fine for many teams. To send richer messages
          — including the actual value that triggered the alert, the
          query name, etc. — open the alert and click <em>Edit</em>.</p>
          <p>Next to <em>Template</em>, change the dropdown from
          <em>Default template</em> to <em>Custom template</em>. Subject
          and body input fields appear.</p>

          <h2>Template variables</h2>
          <p>Both static text and the following variables are supported:</p>
          <ul>
            <li><code>{{ALERT_STATUS}}</code> — the evaluated alert status.</li>
            <li><code>{{ALERT_CONDITION}}</code> — the alert condition operator.</li>
            <li><code>{{ALERT_THRESHOLD}}</code> — the alert threshold value.</li>
            <li><code>{{ALERT_NAME}}</code> — the alert name.</li>
            <li><code>{{ALERT_URL}}</code> — direct URL to the alert page.</li>
            <li><code>{{QUERY_NAME}}</code> — the underlying query name.</li>
            <li><code>{{QUERY_URL}}</code> — direct URL to the query page.</li>
            <li><code>{{QUERY_RESULT_VALUE}}</code> — the value that triggered the alert.</li>
            <li><code>{{QUERY_RESULT_ROWS}}</code> — every row of the result, as an array.</li>
            <li><code>{{QUERY_RESULT_COLS}}</code> — every column of the result, as an array.</li>
            <li><code>{{QUERY_RESULT_TABLE}}</code> — the entire result as a 2D array.</li>
          </ul>

          <h2>Examples</h2>
          <p>A subject line that immediately conveys what changed:</p>
          <pre><code>Alert "{{ALERT_NAME}}" changed status to {{ALERT_STATUS}}</code></pre>
          <p>A Slack-friendly body:</p>
          <pre><code>:rotating_light: <em>{{ALERT_NAME}}</em>
{{QUERY_NAME}} returned <strong>{{QUERY_RESULT_VALUE}}</strong>
&lt;{{QUERY_URL}}|Open the query&gt;</code></pre>
          <p>Click the <em>Preview</em> toggle to see the rendered
          template against the latest query result. The preview is
          purely a sanity check on variable substitution — each
          destination renders the message slightly differently, so
          formatting in the preview will not exactly match what arrives
          in your inbox / Slack channel / webhook.</p>
          <p>To revert to the default templates, change the dropdown
          back to <em>Default template</em> at any time.</p>
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
        title: "Authentication Options (SSO, Google OAuth, SAML)",
        summary:
          "Built-in password auth, Google OAuth and SAML 2.0 sign-in.",
        body: `
          <p>Authentication options are configured through a mix of UI
          settings and environment variables. UI settings live under
          <em>Settings → General</em> and are visible only to admins.
          Some options only appear in the UI once their environment
          variables have been set.</p>

          <h2>Password login</h2>
          <p>By default, users sign in with email and password
          (the <em>Password Login</em> toggle on the General tab).
          Hashed passwords are stored locally for accounts created via
          this flow.</p>
          <p>Users created automatically the first time they sign in via
          SAML or Google have <em>no</em> stored password — this is
          called Just-in-Time (JIT) provisioning. Such users can only
          sign in via the third-party service.</p>
          <p>If you enable Google OAuth or SAML <em>after</em> letting
          users sign up with passwords, the same email may end up with
          two valid credentials (the original local password plus the
          new SSO password). Disable Password Login once SSO is in place
          to keep things simple.</p>

          <h2>Google login (OAuth)</h2>
          <p>You can let any user with a Google account from one or more
          domains sign in. If they don't have a local account yet, one
          is created automatically.</p>
          <ol>
            <li>Open the <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener">Google Cloud credentials page</a> and either pick or create a project, then create OAuth credentials.</li>
            <li>Set the authorised redirect URL to <code>http(s)://&lt;your-host&gt;/oauth/google_callback</code>.</li>
            <li>Set <code>REDASH_GOOGLE_CLIENT_ID</code> and <code>REDASH_GOOGLE_CLIENT_SECRET</code> in your environment with the values Google generates.</li>
            <li>Restart the server.</li>
            <li><em>(Optional)</em> List allowed domains under <em>Settings → General → Allowed Google Apps Domains</em>. Without this step, only users with an existing local account can sign in via Google; with it, accounts are auto-provisioned for any user from a listed domain.</li>
          </ol>

          <h2>SAML 2.0</h2>
          <p>The app can authenticate users against any IdP that speaks
          SAML 2.0. The IdP needs a callback URL of
          <code>/saml/callback?org_slug=&lt;organization&gt;</code>
          (the slug is <code>default</code> unless you've changed it).</p>
          <p>Map the IdP attributes <code>FirstName</code>,
          <code>LastName</code>, and optionally a groups attribute. The
          NameID format is <code>emailAddress</code>.</p>
          <p>Users provisioned via SAML join the default group unless
          the groups attribute lists them elsewhere; passing the groups
          attribute overwrites the existing memberships, so make sure
          the IdP's source of truth is up to date.</p>

          <h3>Static vs dynamic configuration</h3>
          <p>Some IdPs publish a metadata URL (Okta calls this "dynamic"
          configuration) where every SAML parameter can be discovered.
          Others require you to enter the SSO URL, Entity ID and x509
          certificate by hand ("static").</p>
          <ul>
            <li><strong>Dynamic</strong> needs three fields: SAML Metadata URL, SAML Entity ID (the URL to your instance), SAML NameID Format.</li>
            <li><strong>Static</strong> needs SAML Single Sign-on URL, SAML Entity ID, SAML x509 cert.</li>
          </ul>

          <h3>Self-hosted SAML</h3>
          <ol>
            <li>SAML Metadata URL → an XML file on your server, e.g. <code>http://your-site.com/auth/realms/&lt;realm&gt;/protocol/saml/descriptor</code></li>
            <li>SAML Entity ID → the entity ID configured for your deployment (any short identifier works, e.g. <code>analytics</code>)</li>
            <li>SAML NameID Format → <code>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</code></li>
          </ol>
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
        summary: "Connect to Amazon Athena via an IAM user and S3 staging bucket.",
        body: `
          <p>Connecting to Amazon Athena requires an IAM user with
          permission to run Athena queries and to read / write the S3
          buckets that hold your data and Athena's staging output.</p>

          <h2>1. Create an IAM policy</h2>
          <p>Create a policy that grants access to the bucket(s) holding
          your data:</p>
          <pre><code>{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": ["arn:aws:s3:::my-bucket/*"]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetBucketLocation",
        "s3:ListBucket"
      ],
      "Resource": ["arn:aws:s3:::my-bucket"]
    }
  ]
}</code></pre>
          <p>Replace <code>my-bucket</code> with your actual bucket
          name. Note that bucket-level and object-level permissions are
          listed separately.</p>

          <h2>2. Create an IAM user</h2>
          <ul>
            <li>In the IAM console, choose <em>Users → Add User</em>.</li>
            <li>Pick a username and tick <em>Programmatic Access</em>.</li>
            <li>Attach the <code>AWSQuicksightAthenaAccess</code> managed policy <em>and</em> the bucket policy you created above.</li>
            <li>Review and create. Note down the access key ID and secret access key.</li>
          </ul>

          <h2>3. Create the data source</h2>
          <p>Pick <em>Athena</em> from the data source catalogue and
          provide:</p>
          <ul>
            <li><strong>AWS Access Key</strong> and <strong>AWS Secret Key</strong> — from step 2.</li>
            <li><strong>AWS Region</strong> — the region you query Athena in.</li>
            <li><strong>S3 Staging Path</strong> — the bucket Athena uses for query results (the same one you use from the AWS console works fine).</li>
          </ul>
          <p>If your schema is governed by AWS Glue, toggle
          <em>Use Glue Data Catalog</em> under <em>Additional Settings</em>
          to make schema refresh work.</p>

          <h2>Troubleshooting</h2>
          <p><strong>"Insufficient permissions to execute the query."</strong>
          The IAM user is missing access to the source S3 bucket.</p>
          <p><strong>Custom staging bucket.</strong> The
          <code>AWSQuicksightAthenaAccess</code> managed policy only
          grants write permission on buckets named
          <code>aws-athena-query-results-*</code>. If you use a
          differently-named staging bucket, attach a custom policy with
          these actions:</p>
          <pre><code>"s3:GetBucketLocation",
"s3:GetObject",
"s3:ListBucket",
"s3:ListBucketMultipartUploads",
"s3:ListMultipartUploadParts",
"s3:AbortMultipartUpload",
"s3:CreateBucket",
"s3:PutObject"</code></pre>
        `,
      },
      {
        id: "ds-bigquery",
        path: "/data-sources/bigquery-setup",
        title: "Google BigQuery",
        summary: "Use a service account to connect to BigQuery.",
        body: `
          <h2>Data source setup</h2>
          <p>The <em>Project ID</em> and <em>JSON Key File</em> fields
          are always required. The JSON key comes from creating a
          Google service account (see below).</p>
          <p>If your schema is very large (more than ~5,000 tables /
          columns), untick <em>Load Schema</em> to keep the editor
          responsive — many browsers slow down or crash on huge
          schemas.</p>
          <p>BigQuery supports both Legacy and Standard SQL. Standard
          SQL is the default; toggle <em>Use Standard SQL</em> off if
          you want Legacy. Need both? Create two data sources, one for
          each dialect.</p>
          <p>Read about Processing Location in the
          <a href="https://cloud.google.com/bigquery/docs/locations" target="_blank" rel="noopener">BigQuery docs</a>.
          A "job not found" error usually means the processing location
          is wrong.</p>
          <p>The optional <em>Scanned Data Limit</em> performs a dry-run
          on every execution and rejects queries that would scan more
          than the configured limit — useful for keeping cost predictable.
          The optional <em>Maximum Billing Tier</em> is forwarded to
          BigQuery; see their
          <a href="https://cloud.google.com/bigquery/docs/reference/rest/v2/Job#jobconfigurationquery" target="_blank" rel="noopener">job configuration reference</a>
          for details.</p>

          <h2>Creating a Google service account</h2>
          <ol>
            <li>Open the <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener">API credentials page</a>; if prompted, pick or create a project.</li>
            <li>Click <em>Create credentials → Service account key</em>.</li>
            <li>Pick the project and assign the <code>BigQuery Admin</code> role from the tree.</li>
            <li>Pick <code>JSON</code> as the key type and hit <em>Create</em>; a <code>.json</code> file downloads to your machine. Upload it when configuring the data source.</li>
          </ol>

          <h2>Permissions and roles</h2>
          <p>Among the predefined BigQuery roles, only the admin role
          has every permission needed (creating queries and listing
          tables). To craft a custom role, grant:</p>
          <ul>
            <li><code>bigquery.jobs.create</code></li>
            <li><code>bigquery.jobs.get</code></li>
            <li><code>bigquery.jobs.update</code></li>
            <li><code>bigquery.datasets.get</code></li>
            <li><code>bigquery.tables.list</code></li>
            <li><code>bigquery.tables.get</code></li>
            <li><code>bigquery.tables.getData</code></li>
          </ul>
        `,
      },
      {
        id: "ds-url",
        path: "/data-sources/querying-urls",
        title: "JSON / URL Data Sources",
        summary: "Query JSON over HTTP using the JSON data source type.",
        body: `
          <p>Sometimes the data you need lives behind an HTTP API rather
          than in a database. The <em>JSON</em> data source lets you
          query any RESTful endpoint that returns JSON.</p>
          <p>All values returned through this data source are treated as
          text — use
          <a href="/help/user-guide/visualizations/formatting-numbers">number formatting</a>
          to render them nicely in tables and charts.</p>

          <h2>Setting up the JSON data source</h2>
          <p>No authentication is required up front: any auth needed by
          the target API goes in HTTP headers inside each query. Create
          a data source of type <em>JSON</em> and pick a name (something
          obvious like "JSON" works fine).</p>
          <p>Native JSON types (numbers, strings, booleans) are
          preserved. Date / timestamp strings are treated as strings
          unless they're already in ISO-8601 format.</p>

          <h2>Writing queries</h2>
          <p>Each query is a small YAML document. Examples below use the
          GitHub API.</p>

          <h3>Return a list of objects</h3>
          <pre><code>url: https://api.github.com/repos/octocat/hello-world/issues</code></pre>

          <h3>Return a single object</h3>
          <pre><code>url: https://api.github.com/repos/octocat/hello-world/issues/1</code></pre>

          <h3>Return only specific fields</h3>
          <pre><code>url: https://api.github.com/repos/octocat/hello-world/issues
fields: [number, title]</code></pre>

          <h3>Drill into a nested object</h3>
          <pre><code>url: https://api.github.com/repos/octocat/hello-world/issues/1
path: assignees</code></pre>

          <h3>Pass query-string parameters</h3>
          <pre><code>url: https://api.github.com/search/issues
params:
  q: is:open type:pr repo:octocat/hello-world
  sort: created
  order: desc</code></pre>

          <h3>Other supported HTTP options</h3>
          <ul>
            <li><code>method</code> — HTTP method (default: <code>get</code>)</li>
            <li><code>headers</code> — request headers as a dict</li>
            <li><code>auth</code> — basic auth as <code>[username, password]</code></li>
            <li><code>params</code> — query-string params as a dict</li>
            <li><code>data</code> — request body as a dict</li>
            <li><code>json</code> — request body as a dict, JSON-encoded</li>
          </ul>

          <h2>The legacy URL data source</h2>
          <p>The older <code>URL</code> data source type is deprecated.
          Existing data sources keep working, but new ones can no longer
          be created — migrate to the JSON type instead.</p>
          <p>If you do need to keep a legacy URL data source running,
          your endpoint must return JSON shaped like:</p>
          <pre><code>{
  "columns": [
    { "name": "date", "type": "date", "friendly_name": "date" },
    { "name": "value", "type": "integer", "friendly_name": "value" }
  ],
  "rows": [
    { "date": "2024-01-30", "value": 40832 }
  ]
}</code></pre>
          <p>Supported column types are <code>text</code>,
          <code>integer</code>, <code>float</code>, <code>boolean</code>,
          <code>string</code>, <code>datetime</code>, <code>date</code>.</p>
        `,
      },
      {
        id: "ds-mongodb",
        path: "/data-sources/mongodb-setup",
        title: "MongoDB",
        summary: "Connect to MongoDB and run find / aggregate queries as JSON.",
        body: `
          <h2>Setup</h2>
          <p>To connect to MongoDB you need at minimum a
          <em>Connection String</em> and a <em>DB Name</em>:</p>
          <ul>
            <li>Plain: <code>mongodb://username:password@hostname:port/dbname</code></li>
            <li>SSL: <code>mongodb://...:port/dbname?ssl=true</code></li>
            <li>SSL + self-signed certificate: <code>mongodb://...:port/dbname?ssl=true&amp;ssl_cert_reqs=CERT_NONE</code></li>
          </ul>
          <p>Additional options can be appended as query string
          parameters; see the
          <a href="https://docs.mongodb.com/manual/reference/connection-string/" target="_blank" rel="noopener">MongoDB connection string docs</a>
          for the full list.</p>
          <p>Yes — DB Name appears both as a separate field and inside
          the connection string. This duplication is required by some
          shared hosting providers (such as MLab).</p>
          <p>Newer versions also expose dedicated <em>Username</em> and
          <em>Password</em> fields. When set, they take precedence over
          the credentials embedded in the connection string, which lets
          you keep secrets out of plaintext config / API responses.</p>

          <h3>MongoDB Atlas</h3>
          <p>For Atlas free-tier clusters use the SRV connection format:</p>
          <pre><code>mongodb+srv://&lt;user&gt;:&lt;password&gt;@&lt;cluster&gt;.mongodb.net/?retryWrites=true</code></pre>

          <h3>Troubleshooting SSL</h3>
          <p>"SSL handshake failed: certificate verify failed" usually
          means the server uses a self-signed certificate. Either
          install a properly signed certificate or append
          <code>ssl_cert_reqs=CERT_NONE</code> to the connection string.</p>

          <h2>Writing queries</h2>
          <p>Each query is a JSON object. The runtime translates it into
          either a <code>db.collection.find()</code> or a
          <code>db.collection.aggregate()</code> call. The mapping is:</p>
          <table>
            <thead><tr><th>Mongo</th><th>Where to set it</th></tr></thead>
            <tbody>
              <tr><td><code>db</code></td><td>Data source setup screen</td></tr>
              <tr><td><code>collection</code></td><td><code>collection</code> key</td></tr>
              <tr><td><code>query</code></td><td><code>query</code> key</td></tr>
              <tr><td><code>projection</code></td><td><code>fields</code> key</td></tr>
              <tr><td><code>.sort()</code></td><td><code>sort</code> key</td></tr>
              <tr><td><code>.skip()</code></td><td><code>skip</code> key</td></tr>
              <tr><td><code>.limit()</code></td><td><code>limit</code> key</td></tr>
              <tr><td><code>db.collection.count()</code></td><td><code>count</code> key (any value)</td></tr>
            </tbody>
          </table>

          <h3>Simple query example</h3>
          <pre><code>{
  "collection": "my_collection",
  "query":      { "type": 1 },
  "fields":     { "_id": 1, "name": 2 },
  "sort":       [{ "name": "date", "direction": -1 }]
}</code></pre>

          <h3>Count example</h3>
          <pre><code>{
  "collection": "my_collection",
  "count": true
}</code></pre>

          <h3>Aggregation example</h3>
          <p>Aggregation uses a syntax close to PyMongo. To preserve
          sort order, use a regular array for <code>$sort</code>
          (converted to a SON object before execution):</p>
          <pre><code>{
  "collection": "things",
  "aggregate": [
    { "$unwind": "$tags" },
    { "$group":  { "_id": "$tags", "count": { "$sum": 1 } } },
    { "$sort":   [
      { "name": "count", "direction": -1 },
      { "name": "_id",   "direction": -1 }
    ]}
  ]
}</code></pre>

          <h3>Extended JSON and <code>$humanTime</code></h3>
          <p><a href="https://docs.mongodb.com/manual/reference/mongodb-extended-json/" target="_blank" rel="noopener">MongoDB Extended JSON</a>
          is supported, plus a custom <code>$humanTime</code> operator:</p>
          <pre><code>{
  "collection": "date_test",
  "query": {
    "lastModified": {
      "$gt": { "$humanTime": "3 years ago" }
    }
  },
  "limit": 100
}</code></pre>
          <p><code>$humanTime</code> accepts human-readable strings
          ("3 years ago", "yesterday"…) or timestamps. It's also needed
          when using Date / Date Time
          <a href="/help/user-guide/querying/query-parameters">parameters</a>
          with MongoDB:
          <code>{"$humanTime": "{{param}} 00:00"}</code> for Date
          parameters (the <code>00:00</code> suffix can be dropped for
          Date Time).</p>

          <h3>Filtering visualizations</h3>
          <p>Project a column with a <code>::filter</code> suffix to
          add a dashboard-style filter on it:</p>
          <pre><code>{
  "collection": "zipcodes",
  "aggregate": [{
    "$project": {
      "_id":  "$_id",
      "city": "$city",
      "loc":  "$loc",
      "pop":  "$pop",
      "state::filter": "$state"
    }
  }]
}</code></pre>

          <h2>Troubleshooting: <em>"Sort exceeded memory limit"</em></h2>
          <p>MongoDB's in-memory sort caps at 100MB. To sort a larger
          result set you need to opt in to disk-based sorting:</p>
          <pre><code>{ ..., "allowDiskUse": true }</code></pre>
        `,
      },
      {
        id: "ds-google-spreadsheets",
        path: "/data-sources/querying-a-google-spreadsheet",
        title: "Google Sheets",
        summary: "Treat a Google Sheet as a data source via a service account.",
        body: `
          <h2>Setup</h2>
          <p>Connecting to Google Sheets requires a Google
          <a href="https://cloud.google.com/iam/docs/understanding-service-accounts" target="_blank" rel="noopener">service account</a>
          so the app can read sheets without any human signing in.
          Service accounts come with a JSON key file you upload during
          data source setup.</p>

          <h3>Creating a service account</h3>
          <ol>
            <li>Open the <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener">API credentials page</a>; pick or create a project.</li>
            <li>Click <em>Create credentials → Service account key</em>.</li>
            <li>Pick the project and assign <em>Project &gt; Viewer</em> as the role.</li>
            <li>Pick <code>JSON</code> as the key type and click <em>Create</em>.</li>
          </ol>
          <p>A <code>.json</code> file downloads. In <em>Settings → Data
          Sources</em>, add a <em>GoogleSpreadsheet</em> data source,
          name it, and upload the file.</p>

          <h2>Querying</h2>
          <p>To load a sheet you need to <strong>share it with the
          service account's email address</strong>. The email is in the
          JSON key file under <code>"client_email"</code>, or on the
          <a href="https://console.cloud.google.com/apis/api/sheets.googleapis.com/credentials" target="_blank" rel="noopener">Google Sheets API credentials page</a>.
          Share like you would with any user.</p>
          <p>Then create a new query against your Google Sheets data
          source. The query body is just the spreadsheet's ID, optionally
          followed by <code>|&lt;tab-index&gt;</code> (zero-based) to
          pick a specific tab:</p>
          <pre><code>1DFuuOMFzNoFQ5EJ2JE2zB79-0uR5zVKvc0EikmvnDgk|0</code></pre>
          <p>That loads the first tab. Use <code>|1</code> for the
          second tab, and so on.</p>
          <p>The spreadsheet ID is the long random-looking string in the
          spreadsheet URL:</p>
          <pre><code>https://docs.google.com/spreadsheets/d/&lt;ID&gt;/edit#gid=0</code></pre>
          <p>If your organization restricts external sharing, create
          the service account inside the same organization to sidestep
          the restriction.</p>

          <h2>Filtering data</h2>
          <p>Sheets are loaded in full — there is no built-in
          server-side filter. To filter or aggregate beyond a pivot
          table, use the
          <a href="/help/user-guide/querying/query-results-data-source">Query Results data source</a>
          to query the result of the Sheets query with SQL.</p>

          <h2>Date parsing</h2>
          <p>Date strings are parsed with
          <a href="https://dateutil.readthedocs.io/en/stable/" target="_blank" rel="noopener">python-dateutil</a>.
          When dates come back wrong, switch the column to ISO-8601 in
          your sheet (or to one of the other formats listed in
          <a href="https://dateutil.readthedocs.io/en/stable/examples.html#parse-examples" target="_blank" rel="noopener">dateutil's parse examples</a>).</p>
        `,
      },
      {
        id: "ds-google-analytics",
        path: "/data-sources/google-analytics-setup",
        title: "Google Analytics",
        summary: "Connect to Google Analytics via a service account.",
        body: `
          <h2>Create a service account</h2>
          <ol>
            <li>Open the <a href="https://console.cloud.google.com/iam-admin/serviceaccounts" target="_blank" rel="noopener">service accounts page</a>; pick a project if prompted.</li>
            <li>Click <em>Create service account</em>.</li>
            <li>Give it a name and tick <em>Furnish a new private key</em>; pick <code>JSON</code> as the key type.</li>
            <li>Click <em>Create</em> — the JSON key downloads to your machine. Store it securely; this is your only copy.</li>
          </ol>

          <h2>Enable the Analytics API</h2>
          <p>Enable the "Analytics API" for the same Google Cloud
          project from the API library.</p>

          <h2>Grant access to your GA view</h2>
          <p>The new service account has an email address that looks
          like <code>quickstart@PROJECT-ID.iam.gserviceaccount.com</code>.
          Add it as a user with
          <a href="https://support.google.com/analytics/answer/2884495" target="_blank" rel="noopener">Read &amp; Analyze</a>
          permission on whatever view you want to query (see
          <a href="https://support.google.com/analytics/answer/1009702" target="_blank" rel="noopener">how to add a user</a>).</p>

          <h2>Create the data source</h2>
          <p>In <em>Settings → Data Sources</em>, add a
          <em>Google Analytics</em> data source and upload the JSON
          key.</p>

          <h2>Writing queries</h2>
          <p>Queries are JSON documents. Use Google's
          <a href="https://ga-dev-tools.appspot.com/query-explorer/" target="_blank" rel="noopener">Query Explorer</a>
          to discover available metrics and dimensions. Once results
          are in, you can post-process them with the
          <a href="/help/user-guide/querying/query-results-data-source">Query Results data source</a>.</p>

          <h3>Top countries by new users (last 30 days)</h3>
          <pre><code>{
  "ids": "ga:97038718",
  "start_date": "30daysAgo",
  "end_date": "yesterday",
  "metrics": "ga:newUsers",
  "dimensions": "ga:country",
  "max_results": 10,
  "sort": "-ga:newUsers"
}</code></pre>

          <h3>New users per day (last 30 days)</h3>
          <pre><code>{
  "ids": "ga:97038718",
  "start_date": "30daysAgo",
  "end_date": "yesterday",
  "metrics": "ga:newUsers",
  "dimensions": "ga:date",
  "sort": "-ga:newUsers"
}</code></pre>
        `,
      },
      {
        id: "ds-axibase",
        path: "/data-sources/axibase-time-series-database",
        title: "Axibase Time Series Database",
        summary: "Connect to Axibase Time Series Database (ATSD).",
        body: `
          <h2>1. Create a read-only user group in ATSD</h2>
          <ol>
            <li>Sign in to the ATSD web interface (<code>https://&lt;atsd-host&gt;:8443</code>).</li>
            <li>Open <em>Admin → User groups</em> and click <em>Create</em>.</li>
            <li>Pick a name (and optional description) for the group.</li>
            <li>Grant the group <em>Read</em> permission on <em>All entities</em>.</li>
            <li>Save.</li>
          </ol>

          <h2>2. Create a user</h2>
          <ol>
            <li>Open <em>Admin → Users</em>, click <em>Create</em>.</li>
            <li>Pick a username and password.</li>
            <li>Add the user to the group you created above (under <em>Entity Permissions</em>).</li>
            <li>Save.</li>
          </ol>

          <h2>3. Create the data source</h2>
          <p>In <em>Settings → Data Sources</em>, add a new data source
          of type <em>Axibase Time Series Database</em> and fill in:</p>
          <table>
            <thead><tr><th>Field</th><th>Default</th><th>Required</th></tr></thead>
            <tbody>
              <tr><td>Username</td><td>—</td><td>Yes</td></tr>
              <tr><td>Password</td><td>—</td><td>Yes</td></tr>
              <tr><td>Metric Limit</td><td>5000</td><td>No — caps how many ATSD metrics show up in the schema browser.</td></tr>
              <tr><td>Metric Filter</td><td>—</td><td>No — limit metrics to those matching an expression.</td></tr>
              <tr><td>Metric Minimum Insert Date</td><td>—</td><td>No — drop metrics whose latest insert is older than the date (ISO format / endtime syntax).</td></tr>
              <tr><td>Protocol</td><td>http</td><td>Yes — <code>http</code> or <code>https</code>.</td></tr>
              <tr><td>Trust SSL Certificate</td><td>false</td><td>No — required for self-signed certs.</td></tr>
              <tr><td>Host</td><td>localhost</td><td>No — the ATSD hostname or IP.</td></tr>
              <tr><td>Port</td><td>8088</td><td>No — typically 8088 (http) or 8443 (https).</td></tr>
              <tr><td>Connection Timeout</td><td>600</td><td>No — in seconds.</td></tr>
            </tbody>
          </table>
          <p>Click <em>Save</em>, then <em>Test</em> to verify the
          connection. Once the test succeeds you can write queries
          against any data stored in ATSD.</p>
        `,
      },
    ],
  },
  {
    id: "admin",
    title: "Self-hosting & Admin",
    topics: [
      {
        id: "admin-mail",
        path: "/open-source/setup",
        title: "Self-hosting Setup & Mail Configuration",
        summary:
          "Provisioning a fresh instance with Docker Compose, plus mail / SSO / HTTPS basics.",
        body: `
          <p>For a basic deployment, plan for a host with at least 4GB
          of RAM and a moderate amount of CPU. Heavier usage means more
          background workers and API processes, which translates into
          more RAM and CPU.</p>

          <h2>Choosing a deployment shape</h2>
          <p>You have a few options when standing up a new instance:</p>
          <ol>
            <li>Pre-baked AWS EC2 AMI</li>
            <li>Pre-baked Google Compute Engine image</li>
            <li>A bootstrap setup script on a clean Linux VM</li>
            <li>Docker (or Docker Compose) directly</li>
          </ol>
          <p>The setup script — the one that powers the AMI / GCE
          images — installs Docker and Docker Compose, downloads a
          recommended <code>compose.yaml</code>, and starts every
          service. It assumes a clean machine; tweak it if you're
          running on a host that already does other things.</p>

          <h2>Docker</h2>
          <p>Every release is also published as a Docker image and can
          run on any container orchestration platform (Kubernetes, ECS,
          plain Docker Compose…).</p>
          <p>If you're not using one of the cloud images, you must set
          your own secret keys before starting:</p>
          <ol>
            <li>Create a <code>.env</code> in the same folder as <code>compose.yaml</code>.</li>
            <li>Put sensitive variables in bash syntax inside it:
              <pre><code>REDASH_SECRET_KEY=...
REDASH_COOKIE_SECRET=...
GOOGLE_CLIENT_ID=...</code></pre>
            </li>
            <li>Do <em>not</em> commit this file to source control.</li>
          </ol>
          <p>A full instance is several services: API server, one or
          more background workers (for query execution), Redis and
          PostgreSQL.</p>

          <h2>First-run setup</h2>
          <p>Once the stack is up, browse to your server's IP / hostname.
          The first screen prompts you to create an admin account —
          finish that wizard before doing any CLI work, otherwise the
          database isn't yet seeded.</p>

          <h2 id="Mail-Configuration">Mail configuration</h2>
          <p>Outgoing mail (invites, password resets, alert
          notifications) is configured via environment variables:</p>
          <ul>
            <li><code>REDASH_MAIL_SERVER</code> (default: <code>localhost</code>)</li>
            <li><code>REDASH_MAIL_PORT</code> (default: <code>25</code>)</li>
            <li><code>REDASH_MAIL_USE_TLS</code> (default: <code>false</code>)</li>
            <li><code>REDASH_MAIL_USE_SSL</code> (default: <code>false</code>)</li>
            <li><code>REDASH_MAIL_USERNAME</code></li>
            <li><code>REDASH_MAIL_PASSWORD</code></li>
            <li><code>REDASH_MAIL_DEFAULT_SENDER</code></li>
          </ul>
          <p>You also need <code>REDASH_HOST</code>, the public base
          URL of the instance (with the protocol), e.g.
          <code>https://analytics.example.com</code>.</p>
          <p>After updating the env file, restart all services with
          <code>docker-compose up -d</code> — a plain
          <code>docker-compose restart</code> does <em>not</em> re-read
          the env file. To verify, run
          <code>docker-compose run --rm server manage send_test_mail</code>.</p>
          <p>For deliverability, route outgoing mail through a real mail
          provider (Amazon SES, Mailgun, SendGrid…).</p>

          <h2>Google OAuth</h2>
          <p>To enable Google sign-in, follow
          <a href="/help/user-guide/users/authentication-options">Authentication Options</a>
          and set:</p>
          <ul>
            <li><code>REDASH_GOOGLE_CLIENT_ID</code></li>
            <li><code>REDASH_GOOGLE_CLIENT_SECRET</code></li>
          </ul>
          <p>Then restart the server (<code>docker-compose up -d server</code>).
          To auto-create accounts for users from a given domain, list
          the domain under <em>Settings → General → Allowed Google Apps
          Domains</em>.</p>

          <h2>HTTPS</h2>
          <p>For any production deployment, terminate TLS at a reverse
          proxy (nginx, Traefik, a cloud load balancer…) and set the
          cookie secret. The exact recipe depends on your environment.</p>

          <h2>Health check</h2>
          <p>The <code>/ping</code> endpoint returns <code>PONG.</code>
          when the server is healthy — useful for liveness / readiness
          probes.</p>

          <h2>Upgrades</h2>
          <p>Plan to upgrade regularly to pick up bug fixes and new
          features. The general flow is: pull the new images, run any
          new database migrations, restart the stack.</p>
        `,
      },
      {
        id: "admin-usage-data",
        path: "/open-source/admin-guide/usage-data",
        title: "Anonymous Usage Data Sharing (Optional)",
        summary:
          "What gets shared when usage stats are enabled, and how to opt out.",
        body: `
          <p>Recent versions can optionally share aggregated, anonymous
          usage statistics with the upstream maintainers as part of the
          version check. This is opt-in.</p>
          <p>If enabled, the payload looks like the example below — only
          counts and types, never user data, query content or PII:</p>
          <pre><code>{
  "current_version": "8-beta.2",
  "usage": {
    "users_count": 1,
    "queries_count": 4,
    "dashboards_count": 1,
    "widgets_count": 1,
    "textbox_count": 0,
    "alerts_count": 0,
    "data_sources":  { "pg": 1, "redshift": 1 },
    "visualization_types": { "TABLE": 4, "COUNTER": 5 },
    "destination_types":   { "slack": 1, "webhook": 2 }
  }
}</code></pre>
          <p>To never share anything, leave the option disabled in the
          admin settings (it's off by default) — or set the
          corresponding environment variable on the server.</p>
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
