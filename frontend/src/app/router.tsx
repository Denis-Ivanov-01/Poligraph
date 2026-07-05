import { lazy, Suspense } from "react";
import { createBrowserRouter } from "react-router-dom";

import { LoadingState } from "../components/common/LoadingState";
import { PublicLayout } from "../components/layout/PublicLayout";
import { DashboardPage } from "../pages/DashboardPage";
import { HomePage } from "../pages/HomePage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { PartiesPage } from "../pages/PartiesPage";
import { PartyDetailsPage } from "../pages/PartyDetailsPage";
import { PoliticianDetailsPage } from "../pages/PoliticianDetailsPage";
import { PoliticiansPage } from "../pages/PoliticiansPage";
import { SearchPage } from "../pages/SearchPage";
import { StatementDetailsPage } from "../pages/StatementDetailsPage";
import { StatementsPage } from "../pages/StatementsPage";

const MethodologyPage = lazy(() =>
  import("../pages/MethodologyPage").then((module) => ({ default: module.MethodologyPage }))
);

export const router = createBrowserRouter([
  {
    path: "/",
    element: <PublicLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "parties", element: <PartiesPage /> },
      { path: "parties/:slug", element: <PartyDetailsPage /> },
      { path: "politicians", element: <PoliticiansPage /> },
      { path: "politicians/:slug", element: <PoliticianDetailsPage /> },
      { path: "statements", element: <StatementsPage /> },
      { path: "statements/:id", element: <StatementDetailsPage /> },
      { path: "dashboard", element: <DashboardPage /> },
      {
        path: "methodology",
        element: (
          <Suspense fallback={<LoadingState />}>
            <MethodologyPage />
          </Suspense>
        )
      },
      { path: "search", element: <SearchPage /> },
      { path: "*", element: <NotFoundPage /> }
    ]
  }
]);
