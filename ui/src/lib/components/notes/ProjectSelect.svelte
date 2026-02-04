<script lang="ts">
	import { api } from '$lib/services/api';
	import type { ProjectList, ProjectResponse } from '$lib/types';
	import { FolderKanban, ChevronDown } from 'lucide-svelte';

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

	function selectProject(projectId: string | null) {
		value = projectId;
		onchange?.(value);
		// Close dropdown by blurring active element
		(document.activeElement as HTMLElement)?.blur();
	}

	let selectedProject = $derived(projects.find(p => p.id === value));
</script>

{#if projects.length > 0}
	<div class="dropdown dropdown-end">
		<button tabindex="0" class="btn btn-ghost btn-sm gap-1.5 min-w-0" title="Project">
			{#if selectedProject}
				<span class="w-2 h-2 rounded-full shrink-0" style:background-color={selectedProject.color}></span>
				<span class="truncate max-w-24">{selectedProject.name}</span>
			{:else}
				<FolderKanban size={14} class="shrink-0" />
				<span>Project</span>
			{/if}
			<ChevronDown size={12} class="shrink-0 opacity-50" />
		</button>
		<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
		<ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box shadow-lg z-10 w-48 p-1 border border-base-300 mt-1 max-h-60 overflow-y-auto flex-nowrap">
			<li>
				<button class={value === null ? 'active' : ''} onclick={() => selectProject(null)}>
					None
				</button>
			</li>
			{#each projects as project}
				<li>
					<button
						class={value === project.id ? 'active' : ''}
						onclick={() => selectProject(project.id)}
					>
						<span class="w-2 h-2 rounded-full shrink-0" style:background-color={project.color}></span>
						<span class="truncate">{project.name}</span>
					</button>
				</li>
			{/each}
		</ul>
	</div>
{/if}
