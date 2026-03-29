import { useState, useEffect, useRef } from 'react';

const WS_URL = 'ws://127.0.0.1:8000/ws/live-feed';

export function useWebSocket() {
  const [wsConnected, setWsConnected] = useState(false);
  const [liveTransactions, setLiveTransactions] = useState([]);
  const wsRef = useRef(null);

  useEffect(() => {
    const connectWebSocket = () => {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setWsConnected(true);
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'transaction') {
          const transaction = data.data;
          setLiveTransactions(prev => [transaction, ...prev].slice(0, 50));
        }
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setWsConnected(false);
        // Reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return { wsConnected, liveTransactions };
}
