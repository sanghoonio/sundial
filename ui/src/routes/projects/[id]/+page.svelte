<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';

	$effect(() => {
		goto(`${base}/projects?id=${page.params.id}`, { replaceState: true });
	});
</script>
