<script lang="ts">
	import { formatHourLabel, isToday } from '$lib/utils/calendar';
	import type { Snippet } from 'svelte';

	interface Props {
		columns: Date[];
		onslotclick?: (date: Date, hour: number) => void;
		showCurrentTime?: boolean;
		children: Snippet<[{ date: Date; columnIndex: number }]>;
		allDayContent?: Snippet<[{ date: Date; columnIndex: number }]>;
	}

	let { columns, onslotclick, showCurrentTime = true, children, allDayContent }: Props = $props();

	const hours = Array.from({ length: 24 }, (_, i) => i);

	let gridEl = $state<HTMLDivElement | null>(null);

	const HOUR_HEIGHT = 48; // 3rem = 48px
	const TOP_PAD = 8; // pt-2

	// Scroll to ~7am on mount
	$effect(() => {
		if (gridEl) {
			gridEl.scrollTop = 7 * HOUR_HEIGHT;
		}
	});

	let currentTimeTop = $derived.by(() => {
		const now = new Date();
		return TOP_PAD + (now.getHours() + now.getMinutes() / 60) * HOUR_HEIGHT;
	});

	let currentDayIndex = $derived.by(() => {
		const now = new Date();
		return columns.findIndex((d) => isToday(d));
	});
</script>

<div class="flex flex-col h-full overflow-hidden">
	<!-- All-day row -->
	{#if allDayContent}
		<div class="flex border-b border-base-300 min-h-8">
			<div class="w-16 shrink-0 text-xs text-base-content/50 text-right pr-2 py-1">all-day</div>
			<div class="grid flex-1" style="grid-template-columns: repeat({columns.length}, 1fr)">
				{#each columns as date, columnIndex}
					<div class="border-l border-base-300/50 px-0.5 py-0.5 min-h-8">
						{@render allDayContent({ date, columnIndex })}
					</div>
				{/each}
			</div>
		</div>
	{/if}

	<!-- Scrollable time grid -->
	<div class="flex-1 overflow-y-auto" bind:this={gridEl}>
		<div class="relative flex pt-2">
			<!-- Time labels -->
			<div class="w-16 shrink-0">
				{#each hours as hour}
					<div class="h-12 relative">
						<span class="absolute -top-2 right-0 pr-2 text-xs text-base-content/50">
							{formatHourLabel(hour)}
						</span>
					</div>
				{/each}
			</div>

			<!-- Column grid -->
			<div class="relative grid flex-1" style="grid-template-columns: repeat({columns.length}, 1fr)">
				<!-- Today highlight covering full height including top padding -->
				{#each columns as col, ci}
					{#if isToday(col)}
						<div
							class="absolute -top-2 bottom-0 bg-primary/5 pointer-events-none"
							style="left: calc({ci} / {columns.length} * 100%); width: calc(1 / {columns.length} * 100%)"
						></div>
					{/if}
				{/each}

				{#each columns as date, columnIndex}
					<div class="border-l border-base-300/50 relative">
						<!-- Hour dividers -->
						{#each hours as hour}
							<!-- svelte-ignore a11y_click_events_have_key_events -->
							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<div
								class="h-12 border-b border-base-300/30 hover:bg-base-200/50 cursor-pointer"
								onclick={() => onslotclick?.(date, hour)}
							></div>
						{/each}

						<!-- Positioned items via children snippet -->
						<div class="absolute inset-0 pointer-events-none">
							{@render children({ date, columnIndex })}
						</div>
					</div>
				{/each}

				<!-- Current time indicator -->
				{#if showCurrentTime && currentDayIndex >= 0}
					<div
						class="absolute left-0 right-0 z-10 pointer-events-none"
						style="top: {currentTimeTop}px"
					>
						<div
							class="h-0.5 bg-error relative"
							style="margin-left: calc({currentDayIndex} / {columns.length} * 100%); width: calc(1 / {columns.length} * 100%)"
						>
							<div class="absolute -left-1 -top-1 w-2.5 h-2.5 rounded-full bg-error"></div>
						</div>
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>
