<script lang="ts">
	import type { HTMLInputAttributes } from 'svelte/elements';

	interface Props extends HTMLInputAttributes {
		value?: string;
		error?: string;
		label?: string;
	}

	let {
		value = $bindable(''),
		error,
		label,
		class: className = '',
		...rest
	}: Props = $props();
</script>

<div>
	{#if label}
		<!-- svelte-ignore a11y_label_has_associated_control -->
		<label class="label">
			<span class="label-text">{label}</span>
		</label>
	{/if}
	<input
		class="input input-bordered w-full {error ? 'input-error' : ''} {className}"
		bind:value
		{...rest}
	/>
	{#if error}
		<p class="text-error text-sm mt-1">{error}</p>
	{/if}
</div>
