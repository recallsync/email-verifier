import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "@/components/layout/Layout";
import { DashboardPage } from "@/pages/DashboardPage";
import { ListDetailPage } from "@/pages/ListDetailPage";
import { NewListPage } from "@/pages/NewListPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { ToolsPage } from "@/pages/ToolsPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="lists/new" element={<NewListPage />} />
          <Route path="lists/:id" element={<ListDetailPage />} />
          <Route path="tools" element={<ToolsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
