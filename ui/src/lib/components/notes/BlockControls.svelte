<script lang="ts">
	import { ArrowUp, ArrowDown, Trash2, ArrowRightLeft, EllipsisVertical } from 'lucide-svelte';

	interface Props {
		index: number;
		total: number;
		blockType: 'md' | 'chat';
		compact?: boolean;
		onmoveup: () => void;
		onmovedown: () => void;
		ondelete: () => void;
		onconvert: () => void;
	}

	let { index, total, blockType, compact = false, onmoveup, onmovedown, ondelete, onconvert }: Props = $props();
</script>

{#if compact}
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
			<div class="dropdown dropdown-right">
				<button class="btn btn-ghost btn-xs btn-square" tabindex="0">
					<EllipsisVertical size={12} />
				</button>
				<ul class="dropdown-content menu bg-base-200 rounded-box z-10 w-40 p-1 shadow-lg">
					<li>
						<button onclick={onconvert}>
							<ArrowRightLeft size={14} />
							{blockType === 'md' ? 'Convert to chat' : 'Convert to text'}
						</button>
					</li>
					<li>
						<button class="text-error" onclick={ondelete}>
							<Trash2 size={14} />
							Delete
						</button>
					</li>
				</ul>
			</div>
		</div>
	</div>
{:else}
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
				class="btn btn-ghost btn-xs btn-square"
				onclick={onconvert}
				title={blockType === 'md' ? 'Convert to chat' : 'Convert to text'}
			>
				<ArrowRightLeft size={12} />
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
{/if}
