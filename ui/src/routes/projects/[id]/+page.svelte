<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';

	$effect(() => {
		goto(`/projects?id=${page.params.id}`, { replaceState: true });
	});
</script>
