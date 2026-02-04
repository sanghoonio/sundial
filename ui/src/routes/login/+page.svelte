<script lang="ts">
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { auth } from '$lib/stores/auth.svelte';
	import { ApiError, api } from '$lib/services/api';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';

	let password = $state('');
	let error = $state('');
	let loading = $state(false);
	let passwordConfigured = $state(true); // Assume configured, hide link by default

	// Check if password is configured to show/hide setup link
	$effect(() => {
		api.get<{ password_configured: boolean }>('/api/auth/status')
			.then((res) => {
				passwordConfigured = res.password_configured;
				if (!res.password_configured) {
					goto(`${base}/setup`);
				}
			})
			.catch(() => {});
	});

	async function handleSubmit(e: Event) {
		e.preventDefault();
		if (!password.trim()) return;
		loading = true;
		error = '';
		try {
			await auth.login(password);
			goto(`${base}/`);
		} catch (err) {
			if (err instanceof ApiError) {
				if (err.detail.includes('No password configured')) {
					goto(`${base}/setup`);
					return;
				}
				error = err.detail;
			} else {
				error = 'Login failed';
			}
		} finally {
			loading = false;
		}
	}
</script>

<div class="min-h-screen flex items-center justify-center bg-base-200">
	<div class="card bg-base-100 shadow-xl w-full max-w-sm">
		<div class="card-body">
			<h1 class="text-center text-2xl font-light text-base-content/70 mb-4">Sundial</h1>
			<form onsubmit={handleSubmit}>
				<div class="form-control mb-4">
					<Input
						type="password"
						placeholder="Password"
						bind:value={password}
						{error}
						autofocus
					/>
				</div>

				<Button type="submit" variant="primary" class="w-full" {loading}>
					Log in
				</Button>
			</form>

			{#if !passwordConfigured}
				<p class="text-center text-sm mt-4 text-base-content/60">
					First time? <a href="{base}/setup" class="link link-primary">Set up password</a>
				</p>
			{/if}
		</div>
	</div>
</div>
