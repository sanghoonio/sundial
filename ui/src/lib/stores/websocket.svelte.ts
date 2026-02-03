import { createWebSocket } from '$lib/services/websocket';
import type { WSMessage } from '$lib/types';
import { toast } from 'svelte-sonner';

const client = createWebSocket();

let connected = $state(false);
let lastMessage = $state<WSMessage | null>(null);

const refreshCallbacks = new Set<() => void>();

client.onMessage((msg) => {
	lastMessage = msg;
	connected = true;

	// Handle AI background processing events
	if (msg.type === 'ai_tags_suggested') {
		const tags = (msg.data.tags as string[]) || [];
		if (tags.length > 0) {
			toast.info(`AI suggested tags: ${tags.join(', ')}`);
		}
	} else if (msg.type === 'ai_tasks_extracted') {
		const tasks = (msg.data.tasks as { id: string; title: string }[]) || [];
		if (tasks.length > 0) {
			toast.info(`AI extracted ${tasks.length} task${tasks.length > 1 ? 's' : ''} from note`);
		}
	} else if (msg.type === 'ai_events_linked') {
		const eventIds = (msg.data.event_ids as string[]) || [];
		if (eventIds.length > 0) {
			toast.info(`AI linked ${eventIds.length} calendar event${eventIds.length > 1 ? 's' : ''} to note`);
		}
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
