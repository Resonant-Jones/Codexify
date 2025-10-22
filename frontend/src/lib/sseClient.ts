/**
 * Minimal SSE Client for Guardian
 * Handles real-time events from /api/events endpoint
 */

import { EventSourcePolyfill } from './guardianEventSource';

export interface SSEEvent {
  type: string;
  data: any;
  timestamp: string;
  status?: string;
  job_id?: number;
  connector_id?: string;
}

export class SSEClient {
  private eventSource: EventSource | null = null;
  private reconnectTimeout: number = 5000;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 10;
  private listeners: Map<string, Set<(event: SSEEvent) => void>> = new Map();
  private isConnecting: boolean = false;

  constructor(private apiKey: string, private baseUrl: string = '') {
    this.baseUrl = baseUrl || (typeof window !== 'undefined' ? window.location.origin : '');
  }

  connect(lastId: number = 0): void {
    if (this.isConnecting || this.eventSource?.readyState === EventSource.OPEN) {
      return;
    }

    this.isConnecting = true;
    const url = `${this.baseUrl}/api/events?last_id=${lastId}`;
    
    try {
      this.eventSource = new EventSourcePolyfill(url, {
        headers: { 'X-API-Key': this.apiKey },
        heartbeatTimeout: 45000,
        withCredentials: false,
      }) as unknown as EventSource;
      this.isConnecting = false;

      this.eventSource.onopen = () => {
        console.log('[SSE] Connected successfully');
        this.reconnectAttempts = 0;
      };

      this.eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleEvent(data);
        } catch (error) {
          console.warn('[SSE] Failed to parse event data:', error);
        }
      };

      this.eventSource.onerror = (error) => {
        console.error('[SSE] Connection error:', error);
        this.handleDisconnection();
      };

    } catch (error) {
      console.error('[SSE] Failed to create EventSource:', error);
      this.isConnecting = false;
      this.scheduleReconnect();
    }
  }

  private handleEvent(event: SSEEvent): void {
    // Handle heartbeat - just log it
    if (event.type === 'heartbeat' || event.type === 'ping') {
      console.debug('[SSE] Heartbeat received');
      return;
    }

    console.log('[SSE] Event received:', event.type, event.data);
    
    // Notify all listeners for this event type
    const listeners = this.listeners.get(event.type);
    if (listeners) {
      listeners.forEach(listener => {
        try {
          listener(event);
        } catch (error) {
          console.error(`[SSE] Error in listener for ${event.type}:`, error);
        }
      });
    }
  }

  private handleDisconnection(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.scheduleReconnect();
    } else {
      console.error('[SSE] Max reconnection attempts reached');
    }
  }

  private scheduleReconnect(): void {
    this.reconnectAttempts++;
    const delay = Math.min(this.reconnectTimeout * this.reconnectAttempts, 30000);
    
    console.log(`[SSE] Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);
    
    setTimeout(() => {
      if (!this.eventSource || this.eventSource.readyState === EventSource.CLOSED) {
        this.connect();
      }
    }, delay);
  }

  on(eventType: string, callback: (event: SSEEvent) => void): () => void {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    
    const listeners = this.listeners.get(eventType)!;
    listeners.add(callback);
    
    // Return unsubscribe function
    return () => {
      listeners.delete(callback);
      if (listeners.size === 0) {
        this.listeners.delete(eventType);
      }
    };
  }

  off(eventType: string, callback: (event: SSEEvent) => void): void {
    const listeners = this.listeners.get(eventType);
    if (listeners) {
      listeners.delete(callback);
      if (listeners.size === 0) {
        this.listeners.delete(eventType);
      }
    }
  }

  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.listeners.clear();
    this.reconnectAttempts = 0;
    console.log('[SSE] Disconnected');
  }

  isConnected(): boolean {
    return this.eventSource?.readyState === EventSource.OPEN;
  }
}

// Singleton instance for the app
let sseClient: SSEClient | null = null;

export function getSSEClient(apiKey: string = 'changeme'): SSEClient {
  if (!sseClient) {
    sseClient = new SSEClient(apiKey);
  }
  return sseClient;
}

export function resetSSEClient(): void {
  if (sseClient) {
    sseClient.disconnect();
    sseClient = null;
  }
}

// Convenience helper to resume from a known event id
export function resumeSSE(lastId: number, apiKey = 'changeme'): SSEClient {
  resetSSEClient();
  const client = getSSEClient(apiKey);
  client.connect(lastId);
  return client;
}
