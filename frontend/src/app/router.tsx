import { lazy, Suspense } from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";

import { LoadingState } from "../components/common/LoadingState";
import { PublicLayout } from "../components/layout/PublicLayout";
import { DashboardPage } from "../pages/DashboardPage";
import { HomePage } from "../pages/HomePage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { PartiesPage } from "../pages/PartiesPage";
import { PartyDetailsPage } from "../pages/PartyDetailsPage";
import { PoliticianDetailsPage } from "../pages/PoliticianDetailsPage";
import { PoliticiansPage } from "../pages/PoliticiansPage";
import { CommitmentDetailsPage } from "../pages/CommitmentDetailsPage";
import { ProgramDetailsPage } from "../pages/ProgramDetailsPage";
import { ProgramsPage } from "../pages/ProgramsPage";
import { SearchPage } from "../pages/SearchPage";
import { StatementDetailsPage } from "../pages/StatementDetailsPage";
import { StatementsPage } from "../pages/StatementsPage";

const StatementsMethodologyPage = lazy(() =>
  import("../pages/StatementsMethodologyPage").then((module) => ({ default: module.StatementsMethodologyPage }))
);
const ProgramsMethodologyPage = lazy(() =>
  import("../pages/ProgramsMethodologyPage").then((module) => ({ default: module.ProgramsMethodologyPage }))
);
const ControversialTopicsMethodologyPage = lazy(() =>
  import("../pages/ControversialTopicsMethodologyPage").then((module) => ({
    default: module.ControversialTopicsMethodologyPage
  }))
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
      { path: "programs", element: <ProgramsPage /> },
      { path: "programs/:programId/commitments/:slug", element: <CommitmentDetailsPage /> },
      { path: "programs/commitments/:slug", element: <CommitmentDetailsPage /> },
      { path: "programs/:id", element: <ProgramDetailsPage /> },
      { path: "dashboard", element: <DashboardPage /> },
      {
        path: "methodology",
        element: <Navigate to="/methodology/statements" replace />
      },
      {
        path: "methodology/statements",
        element: (
          <Suspense fallback={<LoadingState />}>
            <StatementsMethodologyPage />
          </Suspense>
        )
      },
      {
        path: "methodology/programs",
        element: (
          <Suspense fallback={<LoadingState />}>
            <ProgramsMethodologyPage />
          </Suspense>
        )
      },
      {
        path: "methodology/controversial-topics",
        element: (
          <Suspense fallback={<LoadingState />}>
            <ControversialTopicsMethodologyPage />
          </Suspense>
        )
      },
      { path: "search", element: <SearchPage /> },
      { path: "*", element: <NotFoundPage /> }
    ]
  }
]);
