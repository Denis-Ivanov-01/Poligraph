import { NavLink, Outlet } from "react-router-dom";

import { Footer } from "./Footer";
import { Header } from "./Header";
import { UmamiAnalytics } from "./UmamiAnalytics";

export function PublicLayout() {
  return (
    <>
      <UmamiAnalytics />
      <Header />
      <main className="page">
        <Outlet />
      </main>
      <Footer />
    </>
  );
}
