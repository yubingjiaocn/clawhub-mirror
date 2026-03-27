import { BrowserRouter, Routes, Route } from "react-router-dom";
import { createRoot } from "react-dom/client";
import { Layout } from "./components/Layout";
import { Home } from "./routes/Home";
import { Skills } from "./routes/Skills";
import { SkillDetail } from "./routes/SkillDetail";
import { Search } from "./routes/Search";
import { Publish } from "./routes/Publish";
import { Admin } from "./routes/Admin";
import { Settings } from "./routes/Settings";
import { Guide } from "./routes/Guide";
import { ApiReference } from "./routes/ApiReference";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <BrowserRouter>
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/skills" element={<Skills />} />
        <Route path="/skills/:slug" element={<SkillDetail />} />
        <Route path="/search" element={<Search />} />
        <Route path="/publish" element={<Publish />} />
        <Route path="/admin" element={<Admin />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/guide" element={<Guide />} />
        <Route path="/api" element={<ApiReference />} />
      </Route>
    </Routes>
  </BrowserRouter>,
);
