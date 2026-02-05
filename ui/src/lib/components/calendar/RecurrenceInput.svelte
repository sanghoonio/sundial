<script lang="ts">
	import { Repeat } from 'lucide-svelte';

	interface Props {
		value: string | null;
		onchange?: (value: string | null) => void;
	}

	let { value = $bindable(null), onchange }: Props = $props();

	type Frequency = '' | 'DAILY' | 'WEEKLY' | 'MONTHLY' | 'YEARLY';
	type EndType = 'never' | 'count' | 'until';

	let frequency = $state<Frequency>('');
	let endType = $state<EndType>('never');
	let count = $state(10);
	let untilDate = $state('');

	// Parse existing RRULE on init
	$effect(() => {
		if (!value) {
			frequency = '';
			endType = 'never';
			count = 10;
			untilDate = '';
			return;
		}
		const parts = value.split(';');
		const map: Record<string, string> = {};
		for (const part of parts) {
			const [k, v] = part.split('=');
			if (k && v) map[k] = v;
		}
		frequency = (map['FREQ'] as Frequency) || '';
		if (map['COUNT']) {
			endType = 'count';
			count = parseInt(map['COUNT'], 10) || 10;
		} else if (map['UNTIL']) {
			endType = 'until';
			// UNTIL is YYYYMMDD or YYYYMMDDTHHMMSSZ
			const u = map['UNTIL'];
			if (u.length >= 8) {
				untilDate = `${u.slice(0, 4)}-${u.slice(4, 6)}-${u.slice(6, 8)}`;
			}
		} else {
			endType = 'never';
		}
	});

	function buildRrule(): string | null {
		if (!frequency) return null;
		let rule = `FREQ=${frequency}`;
		if (endType === 'count' && count > 0) {
			rule += `;COUNT=${count}`;
		} else if (endType === 'until' && untilDate) {
			const d = untilDate.replace(/-/g, '');
			rule += `;UNTIL=${d}T235959Z`;
		}
		return rule;
	}

	function handleChange() {
		const newValue = buildRrule();
		value = newValue;
		onchange?.(newValue);
	}
</script>

<div class="flex flex-col gap-1.5">
	<label class="label py-0 flex items-center gap-1.5">
		<Repeat size={12} class="text-base-content/60" />
		<span class="label-text text-xs">Recurrence</span>
	</label>
	<select
		class="select select-bordered select-xs w-full"
		bind:value={frequency}
		onchange={handleChange}
	>
		<option value="">No repeat</option>
		<option value="DAILY">Daily</option>
		<option value="WEEKLY">Weekly</option>
		<option value="MONTHLY">Monthly</option>
		<option value="YEARLY">Yearly</option>
	</select>

	{#if frequency}
		<div class="flex flex-col gap-1.5 pl-2">
			<!-- svelte-ignore a11y_label_has_associated_control -->
			<label class="label py-0"><span class="label-text text-xs">Ends</span></label>
			<select
				class="select select-bordered select-xs w-full"
				bind:value={endType}
				onchange={handleChange}
			>
				<option value="never">Never</option>
				<option value="count">After N occurrences</option>
				<option value="until">On date</option>
			</select>

			{#if endType === 'count'}
				<input
					type="number"
					class="input input-bordered input-xs w-full"
					min="1"
					max="999"
					bind:value={count}
					onchange={handleChange}
				/>
			{:else if endType === 'until'}
				<input
					type="date"
					class="input input-bordered input-xs w-full"
					bind:value={untilDate}
					onchange={handleChange}
				/>
			{/if}
		</div>
	{/if}
</div>
