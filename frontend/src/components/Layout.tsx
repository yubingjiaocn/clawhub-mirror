import { Outlet } from "react-router-dom";
import Header from "./Header";
import { Footer } from "./Footer";

export function Layout() {
  return (
    <div className="app-shell">
      <Header />
      <Outlet />
      <Footer />
    </div>
  );
}
