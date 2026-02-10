import { createWebSocket } from '$lib/services/websocket';
import type { WSMessage } from '$lib/types';
import { toast } from 'svelte-sonner';

const client = createWebSocket();

let connected = $state(false);
let lastMessage = $state<WSMessage | null>(null);

const refreshCallbacks = new Set<() => void>();

interface Sub {
	cb: (data: Record<string, unknown>) => void;
	debounceMs: number;
	timer: ReturnType<typeof setTimeout> | null;
	lastData: Record<string, unknown>;
}

const subscriptions = new Map<string, Set<Sub>>();

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

	// Dispatch to typed subscriptions
	const subs = subscriptions.get(msg.type);
	if (subs) {
		for (const sub of subs) {
			sub.lastData = msg.data;
			if (sub.timer) clearTimeout(sub.timer);
			if (sub.debounceMs <= 0) {
				sub.cb(sub.lastData);
			} else {
				sub.timer = setTimeout(() => {
					sub.timer = null;
					sub.cb(sub.lastData);
				}, sub.debounceMs);
			}
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
	},

	on(eventTypes: string[], cb: (data: Record<string, unknown>) => void, debounceMs = 300): () => void {
		const sub: Sub = { cb, debounceMs, timer: null, lastData: {} };
		for (const type of eventTypes) {
			let set = subscriptions.get(type);
			if (!set) {
				set = new Set();
				subscriptions.set(type, set);
			}
			set.add(sub);
		}
		return () => {
			if (sub.timer) clearTimeout(sub.timer);
			for (const type of eventTypes) {
				subscriptions.get(type)?.delete(sub);
			}
		};
	}
};
