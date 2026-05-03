export default function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="footer">
      <div className="container footer__inner">
        <span>© {year} — Built alongside our analytics platform.</span>
        <span className="muted">Help &amp; landing site for the team.</span>
      </div>
    </footer>
  );
}
