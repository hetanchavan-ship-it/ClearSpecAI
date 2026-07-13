import "@/App.css";

import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";

import AuthPage from "@/pages/AuthPage";
import LandingPage from "@/pages/LandingPage";
import Workstation from "@/pages/Workstation";

const Loading = () => (
  <div className="flex h-screen items-center justify-center bg-[#FAFAF7]">
    <div className="flex items-center gap-3">
      <div className="h-2 w-2 animate-pulse bg-klein" />
      <span className="font-mono text-xs uppercase tracking-[0.2em] text-gray-500">
        Loading ClearSpec
      </span>
    </div>
  </div>
);

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return <Loading />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

const PublicOnlyRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return <Loading />;
  }

  if (user) {
    return <Navigate to="/app" replace />;
  }

  return children;
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/" element={<LandingPage />} />

            <Route
              path="/login"
              element={
                <PublicOnlyRoute>
                  <AuthPage mode="login" />
                </PublicOnlyRoute>
              }
            />

            <Route
              path="/register"
              element={
                <PublicOnlyRoute>
                  <AuthPage mode="register" />
                </PublicOnlyRoute>
              }
            />

            <Route
              path="/app"
              element={
                <ProtectedRoute>
                  <Workstation />
                </ProtectedRoute>
              }
            />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>

          <Toaster position="top-right" richColors />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;