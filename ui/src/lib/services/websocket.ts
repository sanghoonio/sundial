import { base } from '$app/paths';
import { clientId } from '$lib/clientId';
import type { WSMessage } from '$lib/types';

type MessageHandler = (msg: WSMessage) => void;

export function createWebSocket() {
	let ws: WebSocket | null = null;
	let reconnectDelay = 1000;
	const maxReconnectDelay = 30000;
	let shouldReconnect = true;
	const handlers = new Set<MessageHandler>();

	function getUrl(): string {
		const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
		return `${protocol}//${location.host}${base}/ws?client_id=${clientId}`;
	}

	function connect() {
		if (ws?.readyState === WebSocket.OPEN || ws?.readyState === WebSocket.CONNECTING) return;

		try {
			ws = new WebSocket(getUrl());
		} catch {
			scheduleReconnect();
			return;
		}

		ws.onopen = () => {
			reconnectDelay = 1000;
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
			if (shouldReconnect) scheduleReconnect();
		};

		ws.onerror = () => {
			ws?.close();
		};
	}

	function scheduleReconnect() {
		if (!shouldReconnect) return;
		setTimeout(() => {
			if (shouldReconnect) connect();
		}, reconnectDelay);
		reconnectDelay = Math.min(reconnectDelay * 2, maxReconnectDelay);
	}

	function disconnect() {
		shouldReconnect = false;
		ws?.close();
		ws = null;
	}

	function onMessage(handler: MessageHandler): () => void {
		handlers.add(handler);
		return () => handlers.delete(handler);
	}

	function isConnected(): boolean {
		return ws?.readyState === WebSocket.OPEN;
	}

	return { connect, disconnect, onMessage, isConnected };
}
