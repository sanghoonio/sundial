<script lang="ts">
	import { onMount } from 'svelte';

	let hours = $state('00');
	let minutes = $state('00');
	let isPM = $state(false);
	let dateString = $state('');

	function updateTime() {
		const now = new Date();
		const hour24 = now.getHours();
		isPM = hour24 >= 12;
		const hour12 = hour24 % 12 || 12;
		hours = hour12.toString().padStart(2, '0');
		minutes = now.getMinutes().toString().padStart(2, '0');
		dateString = now.toLocaleDateString('en-US', {
			weekday: 'long',
			month: 'long',
			day: 'numeric'
		});
	}

	onMount(() => {
		updateTime();
		const interval = setInterval(updateTime, 1000);
		return () => clearInterval(interval);
	});
</script>

<div class="flip-clock-housing">
	<div class="clock-digits">
		<!-- Hours -->
		<div class="flip-digit">
			<span class="digit-top">{hours[0]}</span>
			<span class="digit-bottom">{hours[0]}</span>
		</div>
		<div class="flip-digit">
			<span class="digit-top">{hours[1]}</span>
			<span class="digit-bottom">{hours[1]}</span>
		</div>

		<!-- Colon -->
		<div class="colon">
			<span></span>
			<span></span>
		</div>

		<!-- Minutes -->
		<div class="flip-digit">
			<span class="digit-top">{minutes[0]}</span>
			<span class="digit-bottom">{minutes[0]}</span>
		</div>
		<div class="flip-digit last-digit">
			<span class="digit-top">{minutes[1]}</span>
			<span class="digit-bottom">{minutes[1]}</span>
			{#if isPM}<span class="ampm">PM</span>{/if}
		</div>
	</div>

	<div class="date-display">{dateString}</div>
</div>

<style>
	.flip-clock-housing {
		display: inline-flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.clock-digits {
		display: flex;
		align-items: center;
		gap: 0.25rem;
	}

	.flip-digit {
		position: relative;
		display: flex;
		flex-direction: column;
		gap: 1.5px;
		width: 2.75rem;
		height: 4rem;
	}

	.ampm {
		position: absolute;
		bottom: 0;
		right: 0.25rem;
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		font-size: 0.5rem;
		font-weight: 500;
		color: #e8e8e8;
		z-index: 10;
	}

	.digit-top,
	.digit-bottom {
		flex: 1;
		display: flex;
		justify-content: center;
		padding-left: 0.05rem;
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		font-size: 2.75rem;
		font-weight: 500;
		line-height: 1;
		color: #e8e8e8;
		overflow: hidden;
		font-variant-numeric: tabular-nums;
		background: #1a1a1a;
	}

	.digit-top {
		align-items: flex-start;
		padding-top: 0.58rem;
		border-radius: 0.375rem 0.375rem 0 0;
	}

	.digit-bottom {
		align-items: flex-end;
		padding-bottom: 0.62rem;
		border-radius: 0 0 0.375rem 0.375rem;
	}

	.colon {
		display: flex;
		flex-direction: column;
		gap: 0.625rem;
		padding: 0 0.25rem;
	}

	.colon span {
		width: 0.375rem;
		height: 0.375rem;
		background: #1a1a1a;
		border-radius: 50%;
	}

	.date-display {
		padding: 0.25rem 0.5rem;
		background: #1a1a1a;
		color: #e8e8e8;
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		font-size: 0.7rem;
		font-weight: 500;
		text-align: center;
		border-radius: 0.25rem;
	}
</style>
