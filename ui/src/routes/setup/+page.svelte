<script lang="ts">
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { auth } from '$lib/stores/auth.svelte';
	import { ApiError, api } from '$lib/services/api';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';

	let password = $state('');
	let confirm = $state('');
	let error = $state('');
	let loading = $state(false);
	let checking = $state(true);

	// Check if password is already configured on mount
	$effect(() => {
		api.get<{ password_configured: boolean }>('/api/auth/status')
			.then((res) => {
				if (res.password_configured) {
					goto(`${base}/login`);
				} else {
					checking = false;
				}
			})
			.catch(() => {
				checking = false;
			});
	});

	async function handleSubmit(e: Event) {
		e.preventDefault();
		if (!password.trim()) return;
		if (password !== confirm) {
			error = 'Passwords do not match';
			return;
		}
		if (password.length < 4) {
			error = 'Password must be at least 4 characters';
			return;
		}
		loading = true;
		error = '';
		try {
			await auth.setup(password);
			goto(`${base}/`);
		} catch (err) {
			if (err instanceof ApiError) {
				if (err.detail.includes('already configured')) {
					goto(`${base}/login`);
					return;
				}
				error = err.detail;
			} else {
				error = 'Setup failed';
			}
		} finally {
			loading = false;
		}
	}
</script>

<div class="min-h-screen flex items-center justify-center bg-base-200">
	{#if checking}
		<span class="loading loading-spinner loading-lg"></span>
	{:else}
		<div class="card bg-base-100 shadow-xl w-full max-w-sm">
			<div class="card-body">
				<h1 class="text-center text-2xl font-light text-base-content/70 mb-4">Sundial</h1>

				<form onsubmit={handleSubmit}>
					<div class="form-control mb-4">
						<Input
							type="password"
							placeholder="Password"
							bind:value={password}
							autofocus
						/>
					</div>

					<div class="form-control mb-4">
						<Input
							type="password"
							placeholder="Confirm password"
							bind:value={confirm}
							error={error}
						/>
					</div>

					<Button type="submit" variant="primary" class="w-full" {loading}>
						Set up
					</Button>
				</form>

				<p class="text-center text-sm mt-4 text-base-content/60">
					Already set up? <a href="{base}/login" class="link link-primary">Log in</a>
				</p>
			</div>
		</div>
	{/if}
</div>
