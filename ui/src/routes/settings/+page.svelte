<script lang="ts">
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';

	function isDesktop() {
		return window.matchMedia('(min-width: 768px)').matches;
	}

	$effect(() => {
		if (isDesktop()) {
			goto(`${base}/settings/account`, { replaceState: true });
		}
	});
</script>
