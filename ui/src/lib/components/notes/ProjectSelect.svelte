<script lang="ts">
	import { api } from '$lib/services/api';
	import type { ProjectList, ProjectResponse } from '$lib/types';
	import { FolderKanban } from 'lucide-svelte';

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
	<label class="btn btn-ghost btn-sm gap-1.5 relative" title="Project">
		<FolderKanban size={14} />
		<span class="text-xs">{projects.find(p => p.id === value)?.name ?? 'None'}</span>
		<select
			class="absolute inset-0 opacity-0 cursor-pointer"
			value={value ?? ''}
			onchange={handleChange}
		>
			<option value="">None</option>
			{#each projects as project}
				<option value={project.id}>{project.name}</option>
			{/each}
		</select>
	</label>
{/if}
