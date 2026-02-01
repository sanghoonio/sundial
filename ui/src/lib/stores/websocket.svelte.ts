import { createWebSocket } from '$lib/services/websocket';
import { toasts } from '$lib/stores/toasts.svelte';
import type { WSMessage } from '$lib/types';

const client = createWebSocket();

let connected = $state(false);
let lastMessage = $state<WSMessage | null>(null);

const refreshCallbacks = new Set<() => void>();

const messageLabels: Record<string, string> = {
	note_created: 'Note created',
	note_deleted: 'Note deleted',
	task_created: 'Task created',
	task_updated: 'Task updated',
	task_deleted: 'Task deleted',
	event_created: 'Event created',
	event_updated: 'Event updated',
	event_deleted: 'Event deleted',
	calendar_synced: 'Calendar synced'
};

client.onMessage((msg) => {
	lastMessage = msg;
	connected = true;

	const label = messageLabels[msg.type];
	if (label) {
		toasts.info(label);
	}

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
