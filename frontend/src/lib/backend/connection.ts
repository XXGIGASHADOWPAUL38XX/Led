import { decodeMessage, encodeMessage, type Message } from "./protocol.ts";

export type ConnectionStatus = "offline" | "connecting" | "connected";

export class BackendConnection {
  private socket: WebSocket | null = null;
  private reconnect: ReturnType<typeof setTimeout> | null = null;
  private stopped = true;
  private sequence = 0;
  private pending = new Map<number, { resolve: (result: unknown) => void; reject: (error: Error) => void; timeout: ReturnType<typeof setTimeout> }>();

  private receive: (message: Message) => void;
  private status: (status: ConnectionStatus) => void;
  constructor(receive: (message: Message) => void, status: (status: ConnectionStatus) => void) {
    this.receive = receive;
    this.status = status;
  }

  start() {
    if (!this.stopped) return;
    this.stopped = false;
    this.open();
  }

  private open() {
    this.status("connecting");
    const url = process.env.NEXT_PUBLIC_BACKEND_URL ?? `ws://${window.location.hostname}:8000/ws`;
    const socket = new WebSocket(url);
    this.socket = socket;
    socket.binaryType = "arraybuffer";
    socket.onopen = () => this.status("connected");
    socket.onmessage = (event) => {
      try {
        const message = decodeMessage(event.data);
        this.receive(message);
        if (message.requestId != null && (message.type === "ack" || message.type === "error")) {
          const request = this.pending.get(message.requestId);
          if (request) {
            clearTimeout(request.timeout);
            this.pending.delete(message.requestId);
            if (message.type === "error") request.reject(Error(String(message.payload.message)));
            else request.resolve(message.payload.result);
          }
        }
      } catch (error) {
        this.receive({ type: "error", payload: { message: error instanceof Error ? error.message : String(error) } });
      }
    };
    socket.onclose = () => {
      if (this.socket !== socket) return;
      this.status("offline");
      this.rejectPending();
      if (!this.stopped) this.reconnect = setTimeout(() => this.open(), 1500);
    };
    socket.onerror = () => socket.close();
  }

  send(type: string, payload: Record<string, unknown>, requestId?: number) {
    if (this.socket?.readyState !== WebSocket.OPEN) throw Error("Backend is disconnected");
    this.socket.send(encodeMessage({ type, payload, ...(requestId === undefined ? {} : { requestId }) }));
  }

  request(type: string, payload: Record<string, unknown> = {}): Promise<unknown> {
    const id = ++this.sequence;
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => { this.pending.delete(id); reject(Error(`${type} timed out`)); }, 30000);
      this.pending.set(id, { resolve, reject, timeout });
      try { this.send(type, payload, id); }
      catch (error) { clearTimeout(timeout); this.pending.delete(id); reject(error); }
    });
  }

  private rejectPending() {
    for (const request of this.pending.values()) { clearTimeout(request.timeout); request.reject(Error("Backend disconnected; command was not replayed")); }
    this.pending.clear();
  }

  stop() {
    this.stopped = true;
    if (this.reconnect) clearTimeout(this.reconnect);
    const socket = this.socket;
    this.socket = null;
    socket?.close();
    this.rejectPending();
    this.status("offline");
  }
}
