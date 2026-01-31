<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLButtonAttributes } from 'svelte/elements';

	interface Props extends HTMLButtonAttributes {
		variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
		size?: 'sm' | 'md' | 'lg';
		loading?: boolean;
		children: Snippet;
	}

	let {
		variant = 'primary',
		size = 'md',
		loading = false,
		disabled,
		children,
		class: className = '',
		...rest
	}: Props = $props();

	const variantClass: Record<string, string> = {
		primary: 'btn-primary',
		secondary: 'btn-secondary',
		ghost: 'btn-ghost',
		danger: 'btn-error'
	};

	const sizeClass: Record<string, string> = {
		sm: 'btn-sm',
		md: '',
		lg: 'btn-lg'
	};
</script>

<button
	class="btn {variantClass[variant]} {sizeClass[size]} {className}"
	disabled={disabled || loading}
	{...rest}
>
	{#if loading}
		<span class="loading loading-spinner loading-sm"></span>
	{/if}
	{@render children()}
</button>
