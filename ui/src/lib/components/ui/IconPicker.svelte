<script lang="ts">
	import ProjectIcon from './ProjectIcon.svelte';
	import { projectIcons } from '$lib/icons';

	interface Props {
		value: string;
		onchange?: (icon: string) => void;
	}

	let { value = $bindable(), onchange }: Props = $props();

	let open = $state(false);

	function select(icon: string) {
		value = icon;
		onchange?.(icon);
		open = false;
	}
</script>

<div class="relative">
	<button
		class="btn btn-ghost btn-sm btn-square"
		onclick={() => (open = !open)}
		title="Change icon"
	>
		<ProjectIcon name={value} size={18} />
	</button>

	{#if open}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="absolute top-full left-0 mt-1 p-2 bg-base-100 border border-base-300 rounded-lg shadow-lg z-30 grid grid-cols-7 gap-1 w-64"
			onmouseleave={() => (open = false)}
		>
			{#each projectIcons as icon}
				<button
					class="w-8 h-8 rounded flex items-center justify-center transition-colors
						{value === icon ? 'bg-primary text-primary-content' : 'hover:bg-base-200 text-base-content/60'}"
					onclick={() => select(icon)}
					title={icon}
				>
					<ProjectIcon name={icon} size={16} />
				</button>
			{/each}
		</div>
	{/if}
</div>
