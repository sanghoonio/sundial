<script lang="ts">
	import { api } from '$lib/services/api';
	import type { ProjectList, ProjectResponse } from '$lib/types';

	interface Props {
		value: string | null;
		onchange?: (projectId: string | null) => void;
	}

	let { value = $bindable(null), onchange }: Props = $props();

	let projects = $state<ProjectResponse[]>([]);

	async function loadProjects() {
		try {
			const res = await api.get<ProjectList>('/api/projects');
			projects = res.projects;
		} catch {
			// ignore
		}
	}

	$effect(() => {
		loadProjects();
	});

	function handleChange(e: Event) {
		const val = (e.target as HTMLSelectElement).value;
		value = val || null;
		onchange?.(value);
	}
</script>

{#if projects.length > 0}
	<select
		class="select select-bordered w-full"
		value={value ?? ''}
		onchange={handleChange}
	>
		<option value="">No project</option>
		{#each projects as project}
			<option value={project.id}>{project.name}</option>
		{/each}
	</select>
{/if}
