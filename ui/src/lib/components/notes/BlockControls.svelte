<script lang="ts">
	import { ArrowUp, ArrowDown, Trash2 } from 'lucide-svelte';

	interface Props {
		index: number;
		total: number;
		onmoveup: () => void;
		onmovedown: () => void;
		ondelete: () => void;
	}

	let { index, total, onmoveup, onmovedown, ondelete }: Props = $props();
</script>

<div class="flex flex-col items-center gap-0.5">
	<span class="text-xs text-base-content/50 font-semibold font-mono select-none">{index + 1}</span>
	<div class="flex flex-col gap-0.5 opacity-0 group-hover/block:opacity-100 transition-opacity">
		<button
			class="btn btn-ghost btn-xs btn-square"
			onclick={onmoveup}
			disabled={index === 0}
			title="Move up"
		>
			<ArrowUp size={12} />
		</button>
		<button
			class="btn btn-ghost btn-xs btn-square"
			onclick={onmovedown}
			disabled={index === total - 1}
			title="Move down"
		>
			<ArrowDown size={12} />
		</button>
		<button
			class="btn btn-ghost btn-xs btn-square text-error"
			onclick={ondelete}
			title="Delete block"
		>
			<Trash2 size={12} />
		</button>
	</div>
</div>
