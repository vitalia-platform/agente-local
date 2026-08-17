import { useState, useEffect, useRef } from 'react';

interface TelemetryEvent {
  event: string;
  [key: string]: any;
}

export function useWebSocket(url: string) {
  const [events, setEvents] = useState<TelemetryEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Resolve relative URL to absolute WS URL if necessary
    const wsUrl = url.startsWith('ws') ? url : `ws://${window.location.host}${url}`;
    
    // For local dev, hardcode to port 8000
    const finalUrl = import.meta.env.DEV ? `ws://localhost:8000${url}` : wsUrl;

    const ws = new WebSocket(finalUrl);
    wsRef.current = ws;

    ws.onopen = () => setIsConnected(true);
    
    ws.onclose = () => setIsConnected(false);
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setEvents(prev => {
          // Keep only last 100 events for memory efficiency
          const newEvents = [data, ...prev];
          return newEvents.slice(0, 100);
        });
      } catch (err) {
        console.error("Failed to parse WS message", err);
      }
    };

    return () => {
      ws.close();
    };
  }, [url]);

  return { events, isConnected };
}
