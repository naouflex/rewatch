import { useEffect } from "react";
import { Route, Routes, useLocation } from "react-router-dom";

import Navbar from "./components/Navbar.jsx";
import Footer from "./components/Footer.jsx";
import Home from "./pages/Home.jsx";
import Work from "./pages/Work.jsx";
import Blog from "./pages/Blog.jsx";
import BlogPost from "./pages/BlogPost.jsx";
import HelpHome from "./pages/HelpHome.jsx";
import HelpPage from "./pages/HelpPage.jsx";
import NotFound from "./pages/NotFound.jsx";
import useEmbedMode from "./hooks/useEmbedMode.js";

export default function App() {
  const embed = useEmbedMode();
  const location = useLocation();

  // Reset scroll on each navigation (Vite SPA does not do this automatically).
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  return (
    <div className={"app-shell" + (embed ? " app-shell--embed" : "")}>
      {!embed && <Navbar />}
      <div className="app-shell__main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/work" element={<Work />} />
          <Route path="/blog" element={<Blog />} />
          <Route path="/blog/:slug" element={<BlogPost />} />
          <Route path="/help" element={<HelpHome />} />
          <Route path="/help/*" element={<HelpPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </div>
      {!embed && <Footer />}
    </div>
  );
}
