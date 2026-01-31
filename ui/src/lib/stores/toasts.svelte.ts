export interface Toast {
	id: number;
	message: string;
	type: 'info' | 'success' | 'error' | 'warning';
}

let nextId = 0;
let items = $state<Toast[]>([]);

export const toasts = {
	get items() { return items; },

	add(message: string, type: Toast['type'] = 'info', duration = 4000) {
		const id = nextId++;
		items = [...items, { id, message, type }];
		if (duration > 0) {
			setTimeout(() => this.remove(id), duration);
		}
		return id;
	},

	remove(id: number) {
		items = items.filter((t) => t.id !== id);
	},

	success(message: string) { return this.add(message, 'success'); },
	error(message: string) { return this.add(message, 'error', 6000); },
	warning(message: string) { return this.add(message, 'warning'); },
	info(message: string) { return this.add(message, 'info'); }
};
