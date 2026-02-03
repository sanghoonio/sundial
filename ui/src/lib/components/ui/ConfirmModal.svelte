<script lang="ts">
	import { confirmModal } from '$lib/stores/confirm.svelte';
	import { Trash2, AlertTriangle } from 'lucide-svelte';

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape' && confirmModal.isOpen) {
			confirmModal.resolve(false);
		}
	}

	const variantStyles = {
		default: {
			icon: null,
			buttonClass: 'btn-primary'
		},
		danger: {
			icon: Trash2,
			buttonClass: 'btn-error'
		},
		warning: {
			icon: AlertTriangle,
			buttonClass: 'btn-warning'
		}
	};

	const style = $derived(variantStyles[confirmModal.variant]);
</script>

<svelte:window onkeydown={handleKeydown} />

<dialog class="modal" class:modal-open={confirmModal.isOpen}>
	<div class="modal-box max-w-sm text-center">
		{#if style.icon}
			<div class="flex justify-center mb-4">
				<div
					class="w-12 h-12 rounded-full flex items-center justify-center
					{confirmModal.variant === 'danger' ? 'bg-error/10 text-error' : 'bg-warning/10 text-warning'}"
				>
					<svelte:component this={style.icon} size={24} />
				</div>
			</div>
		{/if}

		<h3 class="font-bold text-lg">{confirmModal.title}</h3>
		<p class="py-4 text-base-content/70">{confirmModal.message}</p>

		<div class="modal-action justify-center gap-2">
			<button class="btn btn-ghost" onclick={() => confirmModal.resolve(false)}>
				{confirmModal.cancelText}
			</button>
			<button class="btn {style.buttonClass}" onclick={() => confirmModal.resolve(true)}>
				{confirmModal.confirmText}
			</button>
		</div>
	</div>
	<form method="dialog" class="modal-backdrop">
		<button onclick={() => confirmModal.resolve(false)}>close</button>
	</form>
</dialog>
