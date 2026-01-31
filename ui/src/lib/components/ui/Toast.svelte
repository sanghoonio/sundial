<script lang="ts">
	import { toasts } from '$lib/stores/toasts.svelte';

	const alertClass: Record<string, string> = {
		info: 'alert-info',
		success: 'alert-success',
		error: 'alert-error',
		warning: 'alert-warning'
	};
</script>

{#if toasts.items.length > 0}
	<div class="toast toast-end toast-bottom z-50">
		{#each toasts.items as toast (toast.id)}
			<div class="alert {alertClass[toast.type]} shadow-lg">
				<span>{toast.message}</span>
				<button class="btn btn-sm btn-ghost" onclick={() => toasts.remove(toast.id)}>✕</button>
			</div>
		{/each}
	</div>
{/if}
