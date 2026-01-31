<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		hoverable?: boolean;
		compact?: boolean;
		class?: string;
		children: Snippet;
	}

	let {
		hoverable = false,
		compact = false,
		class: className = '',
		children
	}: Props = $props();
</script>

<div
	class="card bg-base-100 shadow-sm border border-base-300 {hoverable ? 'hover:shadow-md transition-shadow cursor-pointer' : ''} {className}"
>
	<div class="card-body {compact ? 'p-4' : ''}">
		{@render children()}
	</div>
</div>
