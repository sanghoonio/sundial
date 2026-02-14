<script lang="ts">
	import { fade, scale } from 'svelte/transition';
	import { Plus, MessageSquare, FileText } from 'lucide-svelte';

	interface Props {
		onaddmd: () => void;
		onaddchat: () => void;
	}

	let { onaddmd, onaddchat }: Props = $props();

	let hovered = $state(false);
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="relative h-4 flex items-center justify-center group/divider"
	onmouseenter={() => (hovered = true)}
	onmouseleave={() => (hovered = false)}
>
	<!-- Line -->
	<div class="absolute inset-x-0 top-1/2 border-t border-base-300/50"></div>

	<!-- Plus icon (always visible) -->
	<div class="relative z-[5] bg-base-100 px-1">
		<Plus size={12} class="text-base-content/20 transition-opacity {hovered ? 'opacity-0' : ''}" />
	</div>

	<!-- Floating button pill (on hover) -->
	{#if hovered}
		<div
			class="absolute z-10 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex items-center gap-1 bg-base-100 border border-base-300 rounded-full px-2 py-0.5 shadow-md"
			in:scale={{ start: 0.9, duration: 150 }}
			out:fade={{ duration: 100 }}
		>
			<button class="btn btn-ghost btn-xs gap-1" onclick={onaddmd} title="Add text block">
				<FileText size={12} />
				<span class="text-xs">Text</span>
			</button>
			<button class="btn btn-ghost btn-xs gap-1" onclick={onaddchat} title="Add chat block">
				<MessageSquare size={12} />
				<span class="text-xs">Chat</span>
			</button>
		</div>
	{/if}
</div>
