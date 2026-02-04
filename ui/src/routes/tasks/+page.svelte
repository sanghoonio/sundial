<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { api } from '$lib/services/api';
	import type { ProjectList } from '$lib/types';

	async function redirect() {
		try {
			const res = await api.get<ProjectList>('/api/projects');
			if (res.projects.length > 0) {
				const taskParam = page.url.searchParams.get('task');
				const url = taskParam
					? `${base}/tasks/${res.projects[0].id}?task=${taskParam}`
					: `${base}/tasks/${res.projects[0].id}`;
				goto(url, { replaceState: true });
			}
		} catch (e) {
			console.error('Failed to load projects', e);
		}
	}

	$effect(() => {
		redirect();
	});
</script>

<div class="flex items-center justify-center py-20">
	<span class="loading loading-spinner loading-lg"></span>
</div>
