<script lang="ts">
	import { goto } from '$app/navigation';

	$effect(() => {
		goto('/settings/account', { replaceState: true });
	});
</script>
