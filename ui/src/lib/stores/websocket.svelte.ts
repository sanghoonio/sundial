import { createWebSocket } from '$lib/services/websocket';
import type { WSMessage } from '$lib/types';

const client = createWebSocket();

let connected = $state(false);
let lastMessage = $state<WSMessage | null>(null);

const refreshCallbacks = new Set<() => void>();

client.onMessage((msg) => {
	lastMessage = msg;
	connected = true;

	refreshCallbacks.forEach((cb) => cb());
});

export const ws = {
	get connected() { return connected; },
	get lastMessage() { return lastMessage; },

	start() {
		client.connect();
	},

	stop() {
		client.disconnect();
		connected = false;
	},

	onRefresh(cb: () => void): () => void {
		refreshCallbacks.add(cb);
		return () => refreshCallbacks.delete(cb);
	}
};
