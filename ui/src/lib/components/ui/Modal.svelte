<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		open: boolean;
		title?: string;
		onclose?: () => void;
		children: Snippet;
	}

	let { open = $bindable(false), title, onclose, children }: Props = $props();

	function handleClose() {
		open = false;
		onclose?.();
	}
</script>

<dialog class="modal" class:modal-open={open}>
	<div class="modal-box">
		{#if title}
			<h3 class="font-bold text-lg mb-4">{title}</h3>
		{/if}
		<button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2" onclick={handleClose}>
			✕
		</button>
		{@render children()}
	</div>
	<form method="dialog" class="modal-backdrop">
		<button onclick={handleClose}>close</button>
	</form>
</dialog>
