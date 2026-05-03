import HelpSidebar from "./HelpSidebar.jsx";

export default function HelpLayout({ children }) {
  return (
    <div className="container help-layout">
      <HelpSidebar />
      <main className="help-content">{children}</main>
    </div>
  );
}
