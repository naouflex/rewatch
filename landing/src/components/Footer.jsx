export default function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="footer">
      <div className="container footer__inner">
        <span>© {year} — Built alongside our Redash deployment.</span>
        <span className="muted">
          Help content adapted from{" "}
          <a
            href="https://redash.io/help"
            target="_blank"
            rel="noopener noreferrer"
          >
            redash.io/help
          </a>
        </span>
      </div>
    </footer>
  );
}
