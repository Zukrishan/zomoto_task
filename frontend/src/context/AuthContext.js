import { createContext, useContext, useState, useEffect } from "react";
import Cookies from "js-cookie";
import { jwtDecode } from "jwt-decode";
import api from "../lib/api";

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      const storedToken = Cookies.get("zomoto_token");
      if (storedToken) {
        try {
          const decoded = jwtDecode(storedToken);
          if (decoded.exp * 1000 > Date.now()) {
            const response = await api.get("/auth/me");
            setUser(response.data);
            setToken(storedToken);
          } else {
            Cookies.remove("zomoto_token");
          }
        } catch (error) {
          console.error("Auth init error:", error);
          Cookies.remove("zomoto_token");
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const login = async (email, password) => {
    const response = await api.post("/auth/login", { email, password });
    const { access_token, user: userData } = response.data;

    Cookies.set("zomoto_token", access_token, { expires: 1 });
    setUser(userData);
    setToken(access_token);

    return userData;
  };

  const logout = () => {
    Cookies.remove("zomoto_token");
    setUser(null);
    setToken(null);
  };

  const value = {
    user,
    token,
    login,
    logout,
    loading,
    isAuthenticated: !!user && !!token,
    isOwner: user?.role === "OWNER",
    isManager: user?.role === "MANAGER",
    isStaff: user?.role === "STAFF",
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
