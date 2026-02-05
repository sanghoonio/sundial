<script lang="ts">
	import { ChevronLeft, ChevronRight, Plus, RefreshCw } from 'lucide-svelte';

	type CalendarView = 'month' | 'week' | 'day' | 'agenda';

	interface Props {
		currentDate: Date;
		view: CalendarView;
		syncing?: boolean;
		onprev: () => void;
		onnext: () => void;
		ontoday: () => void;
		onviewchange: (view: CalendarView) => void;
		onnewevent: () => void;
		onsync?: () => void;
	}

	let { currentDate, view, syncing = false, onprev, onnext, ontoday, onviewchange, onnewevent, onsync }: Props = $props();

	let label = $derived.by(() => {
		if (view === 'day') {
			return currentDate.toLocaleDateString(undefined, {
				weekday: 'long',
				month: 'long',
				day: 'numeric',
				year: 'numeric'
			});
		}
		if (view === 'week') {
			const start = new Date(currentDate);
			start.setDate(start.getDate() - start.getDay());
			const end = new Date(start);
			end.setDate(end.getDate() + 6);
			if (start.getMonth() === end.getMonth()) {
				return `${start.toLocaleDateString(undefined, { month: 'long' })} ${start.getDate()}–${end.getDate()}, ${start.getFullYear()}`;
			}
			return `${start.toLocaleDateString(undefined, { month: 'short' })} ${start.getDate()} – ${end.toLocaleDateString(undefined, { month: 'short' })} ${end.getDate()}, ${end.getFullYear()}`;
		}
		return currentDate.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
	});

	const views: CalendarView[] = ['month', 'week', 'day', 'agenda'];
</script>

<div class="relative border-b border-base-300 shrink-0">
	<!-- Desktop layout: original centered grid -->
	<div class="hidden md:grid grid-cols-[1fr_auto_1fr] items-center px-4 lg:pr-68 py-3">
		<div class="flex items-center gap-2">
			<h2 class="text-lg font-semibold">{label}</h2>
		</div>

		<div class="flex items-center gap-1">
			<button class="btn btn-ghost btn-sm btn-square" onclick={onprev}>
				<ChevronLeft size={18} />
			</button>
			<button class="btn btn-ghost btn-sm" onclick={ontoday}>Today</button>
			<button class="btn btn-ghost btn-sm btn-square" onclick={onnext}>
				<ChevronRight size={18} />
			</button>
		</div>

		<div></div>
	</div>

	<!-- Desktop: absolute right section -->
	<div class="absolute right-4 top-1/2 -translate-y-1/2 hidden md:flex items-center gap-2">
		{#if onsync}
			<button
				class="btn btn-ghost btn-sm btn-square"
				onclick={onsync}
				disabled={syncing}
				title="Sync calendar"
			>
				<RefreshCw size={16} class={syncing ? 'animate-spin' : ''} />
			</button>
		{/if}
		{#each views as v}
			<button
				class="btn btn-ghost btn-sm {view === v ? 'btn-active' : ''}"
				onclick={() => onviewchange(v)}
			>
				{v.charAt(0).toUpperCase() + v.slice(1)}
			</button>
		{/each}
		<button class="btn btn-primary btn-sm" onclick={onnewevent}>
			<Plus size={16} />
			Event
		</button>
	</div>

	<!-- Mobile layout -->
	<div class="md:hidden px-4 py-3">
		<!-- Row 1: date + nav + new event -->
		<div class="flex items-center justify-between gap-2">
			<h2 class="text-base font-semibold truncate">{label}</h2>
			<div class="flex items-center gap-1 shrink-0">
				<button class="btn btn-ghost btn-sm btn-square" onclick={onprev}>
					<ChevronLeft size={18} />
				</button>
				<button class="btn btn-ghost btn-sm" onclick={ontoday}>Today</button>
				<button class="btn btn-ghost btn-sm btn-square" onclick={onnext}>
					<ChevronRight size={18} />
				</button>
				<button class="btn btn-primary btn-sm" onclick={onnewevent}>
					<Plus size={16} />
				</button>
			</div>
		</div>
		<!-- Row 2: view switcher + sync -->
		<div class="flex items-center gap-1 mt-2">
			{#each views as v}
				<button
					class="btn btn-ghost btn-xs {view === v ? 'btn-active' : ''}"
					onclick={() => onviewchange(v)}
				>
					{v.charAt(0).toUpperCase() + v.slice(1)}
				</button>
			{/each}
			{#if onsync}
				<button
					class="btn btn-ghost btn-xs btn-square ml-auto"
					onclick={onsync}
					disabled={syncing}
					title="Sync calendar"
				>
					<RefreshCw size={14} class={syncing ? 'animate-spin' : ''} />
				</button>
			{/if}
		</div>
	</div>
</div>
