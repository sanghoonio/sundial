export const projectIcons = [
	'folder-kanban', 'code', 'briefcase', 'rocket', 'book-open', 'palette',
	'music', 'camera', 'heart', 'star', 'zap', 'globe', 'shopping-cart', 'wrench',
	'lightbulb', 'target', 'trophy', 'flame', 'leaf', 'coffee', 'gamepad-2',
	'graduation-cap', 'megaphone', 'pen-tool', 'shield', 'smartphone', 'box', 'layers'
] as const;

export type ProjectIconName = typeof projectIcons[number];
