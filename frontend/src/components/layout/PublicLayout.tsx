import { NavLink, Outlet } from "react-router-dom";

import { Footer } from "./Footer";
import { Header } from "./Header";

export function PublicLayout() {
  return (
    <>
      <Header />
      <main className="page">
        <Outlet />
      </main>
      <Footer />
    </>
  );
}
