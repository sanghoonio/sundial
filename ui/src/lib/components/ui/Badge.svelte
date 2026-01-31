<script lang="ts">
	interface Props {
		variant?: 'primary' | 'secondary' | 'ghost' | 'accent' | 'info';
		removable?: boolean;
		onremove?: () => void;
		class?: string;
		children: import('svelte').Snippet;
	}

	let {
		variant = 'ghost',
		removable = false,
		onremove,
		class: className = '',
		children
	}: Props = $props();

	const variantClass: Record<string, string> = {
		primary: 'badge-primary',
		secondary: 'badge-secondary',
		ghost: 'badge-ghost',
		accent: 'badge-accent',
		info: 'badge-info'
	};
</script>

<span class="badge {variantClass[variant]} gap-1 {className}">
	{@render children()}
	{#if removable}
		<button class="cursor-pointer" onclick={onremove}>
			✕
		</button>
	{/if}
</span>
