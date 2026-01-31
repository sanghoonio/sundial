<script lang="ts">
	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth.svelte';
	import { ApiError } from '$lib/services/api';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';

	let password = $state('');
	let confirm = $state('');
	let error = $state('');
	let loading = $state(false);

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
			goto('/');
		} catch (err) {
			if (err instanceof ApiError) {
				if (err.detail.includes('already configured')) {
					goto('/login');
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
	<div class="card bg-base-100 shadow-xl w-full max-w-sm">
		<div class="card-body">
			<h1 class="text-2xl font-bold text-center mb-2">Sundial</h1>
			<p class="text-center text-base-content/60 mb-6">Create a password to get started</p>

			<form onsubmit={handleSubmit}>
				<div class="form-control mb-3">
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
				Already set up? <a href="/login" class="link link-primary">Log in</a>
			</p>
		</div>
	</div>
</div>
