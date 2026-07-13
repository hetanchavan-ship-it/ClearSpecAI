import { createContext, useContext, useEffect, useState } from "react";
import { authApi } from "@/lib/api";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("cs_token");

    if (!token) {
      setLoading(false);
      return;
    }

    authApi
      .me()
      .then((userData) => {
        setUser(userData);
      })
      .catch(() => {
        localStorage.removeItem("cs_token");
        setUser(null);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const login = async (email, password) => {
    const { token, user } = await authApi.login({ email, password });

    localStorage.setItem("cs_token", token);
    setUser(user);

    return user;
  };

  const register = async (name, email, password) => {
    const { token, user } = await authApi.register({
      name,
      email,
      password,
    });

    localStorage.setItem("cs_token", token);
    setUser(user);

    return user;
  };

  const logout = () => {
    localStorage.removeItem("cs_token");
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }

  return context;
};