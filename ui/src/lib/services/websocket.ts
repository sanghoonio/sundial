import { base } from '$app/paths';
import { clientId } from '$lib/clientId';
import type { WSMessage } from '$lib/types';

type MessageHandler = (msg: WSMessage) => void;
type ConnectionState = 'connected' | 'reconnecting' | 'disconnected';
type StateHandler = (state: ConnectionState) => void;

export function createWebSocket() {
	let ws: WebSocket | null = null;
	let reconnectDelay = 1000;
	const maxReconnectDelay = 30000;
	let shouldReconnect = true;
	let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
	const handlers = new Set<MessageHandler>();
	const stateHandlers = new Set<StateHandler>();

	function fireState(state: ConnectionState) {
		stateHandlers.forEach((h) => h(state));
	}

	function getUrl(): string {
		const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
		return `${protocol}//${location.host}${base}/ws?client_id=${clientId}`;
	}

	function connect() {
		if (ws?.readyState === WebSocket.OPEN || ws?.readyState === WebSocket.CONNECTING) return;

		try {
			ws = new WebSocket(getUrl());
		} catch {
			fireState('reconnecting');
			scheduleReconnect();
			return;
		}

		ws.onopen = () => {
			reconnectDelay = 1000;
			fireState('connected');
		};

		ws.onmessage = (event) => {
			try {
				const msg: WSMessage = JSON.parse(event.data);
				handlers.forEach((h) => h(msg));
			} catch {
				// ignore invalid messages
			}
		};

		ws.onclose = () => {
			ws = null;
			if (shouldReconnect) {
				fireState('reconnecting');
				scheduleReconnect();
			} else {
				fireState('disconnected');
			}
		};

		ws.onerror = () => {
			ws?.close();
		};
	}

	function clearReconnectTimer() {
		if (reconnectTimer) {
			clearTimeout(reconnectTimer);
			reconnectTimer = null;
		}
	}

	function scheduleReconnect() {
		if (!shouldReconnect) return;
		clearReconnectTimer();
		reconnectTimer = setTimeout(() => {
			reconnectTimer = null;
			if (shouldReconnect) connect();
		}, reconnectDelay);
		reconnectDelay = Math.min(reconnectDelay * 2, maxReconnectDelay);
	}

	function disconnect() {
		shouldReconnect = false;
		clearReconnectTimer();
		ws?.close();
		ws = null;
	}

	function reconnect() {
		clearReconnectTimer();
		ws?.close();
		ws = null;
		reconnectDelay = 1000;
		shouldReconnect = true;
		connect();
	}

	function onMessage(handler: MessageHandler): () => void {
		handlers.add(handler);
		return () => handlers.delete(handler);
	}

	function onStateChange(handler: StateHandler): () => void {
		stateHandlers.add(handler);
		return () => stateHandlers.delete(handler);
	}

	function isConnected(): boolean {
		return ws?.readyState === WebSocket.OPEN;
	}

	return { connect, disconnect, reconnect, onMessage, onStateChange, isConnected };
}
