import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  useCallback,
} from "react";
import { useAuth } from "./AuthContext";

const WebSocketContext = createContext(null);

export function WebSocketProvider({ children }) {
  const { token, isAuthenticated } = useAuth();
  const ws = useRef(null);
  const reconnectTimer = useRef(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const listeners = useRef(new Map());

  // Get WebSocket URL from backend URL
  const getWsUrl = useCallback(() => {
    const backendUrl = process.env.REACT_APP_BACKEND_URL || "";
    // Convert http(s) to ws(s)
    const wsUrl = backendUrl.replace(/^http/, "ws");
    // Use /api/ws to route through the ingress proxy
    return `${wsUrl}/api/ws/${token}`;
  }, [token]);

  const connect = useCallback(() => {
    if (!token || !isAuthenticated) return;

    // Don't create new connection if already connected
    if (ws.current?.readyState === WebSocket.OPEN) return;

    try {
      const wsUrl = getWsUrl();
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log("WebSocket connected");
        setIsConnected(true);
        // Clear reconnect timer
        if (reconnectTimer.current) {
          clearTimeout(reconnectTimer.current);
          reconnectTimer.current = null;
        }
      };

      ws.current.onmessage = (event) => {
        try {
          // Handle pong response
          if (event.data === "pong") {
            return;
          }

          const message = JSON.parse(event.data);
          console.log(
            "WebSocket received:",
            message.type,
            message.data?.title || message.data?.id || "",
          );
          setLastMessage(message);

          // Notify all listeners for this message type
          const typeListeners = listeners.current.get(message.type) || [];
          console.log(`Listeners for ${message.type}:`, typeListeners.length);
          typeListeners.forEach((callback) => callback(message));

          // Also notify "all" listeners
          const allListeners = listeners.current.get("*") || [];
          allListeners.forEach((callback) => callback(message));
        } catch (e) {
          console.error("Failed to parse WebSocket message:", e, event.data);
        }
      };

      ws.current.onclose = (event) => {
        console.log("WebSocket disconnected:", event.code);
        setIsConnected(false);
        ws.current = null;

        // Reconnect after delay (only if still authenticated)
        if (isAuthenticated && event.code !== 4001) {
          reconnectTimer.current = setTimeout(() => {
            console.log("Attempting to reconnect...");
            connect();
          }, 3000);
        }
      };

      ws.current.onerror = (error) => {
        console.error("WebSocket error:", error);
      };
    } catch (error) {
      console.error("Failed to create WebSocket:", error);
    }
  }, [token, isAuthenticated, getWsUrl]);

  const disconnect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }
    setIsConnected(false);
  }, []);

  // Connect when authenticated
  useEffect(() => {
    if (isAuthenticated && token) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [isAuthenticated, token, connect, disconnect]);

  // Send ping every 30 seconds to keep connection alive
  useEffect(() => {
    if (!isConnected) return;

    const pingInterval = setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send("ping");
      }
    }, 30000);

    return () => clearInterval(pingInterval);
  }, [isConnected]);

  // Subscribe to specific message types
  const subscribe = useCallback((type, callback) => {
    if (!listeners.current.has(type)) {
      listeners.current.set(type, []);
    }
    listeners.current.get(type).push(callback);

    // Return unsubscribe function
    return () => {
      const typeListeners = listeners.current.get(type) || [];
      const index = typeListeners.indexOf(callback);
      if (index > -1) {
        typeListeners.splice(index, 1);
      }
    };
  }, []);

  // Send message through WebSocket
  const send = useCallback((message) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(
        typeof message === "string" ? message : JSON.stringify(message),
      );
    }
  }, []);

  const value = {
    isConnected,
    lastMessage,
    subscribe,
    send,
    reconnect: connect,
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocket() {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error("useWebSocket must be used within a WebSocketProvider");
  }
  return context;
}

// Hook for subscribing to specific event types
export function useWebSocketEvent(eventType, callback) {
  const { subscribe } = useWebSocket();

  useEffect(() => {
    const unsubscribe = subscribe(eventType, callback);
    return unsubscribe;
  }, [eventType, callback, subscribe]);
}
