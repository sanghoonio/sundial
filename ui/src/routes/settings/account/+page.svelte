<script lang="ts">
	import { base } from '$app/paths';
	import { api } from '$lib/services/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { UserResponse } from '$lib/types';
	import Button from '$lib/components/ui/Button.svelte';
	import { ChevronLeft, Save, Check } from 'lucide-svelte';

	let username = $state('');
	let usernameStatus: 'idle' | 'saving' | 'saved' | 'error' = $state('idle');
	let showSavedText = $state(false);
	let usernameMsg = $state<{ type: 'success' | 'error'; text: string } | null>(null);
	let currentPassword = $state('');
	let newPassword = $state('');
	let confirmPassword = $state('');
	let savingPassword = $state(false);
	let passwordMsg = $state<{ type: 'success' | 'error'; text: string } | null>(null);

	$effect(() => {
		username = auth.user?.username || 'admin';
	});

	async function handleSaveUsername() {
		usernameStatus = 'saving';
		usernameMsg = null;
		try {
			const updated = await api.put<UserResponse>('/api/auth/username', { username });
			auth.setUser(updated);
			usernameMsg = { type: 'success', text: 'Username updated' };
			usernameStatus = 'saved';
			showSavedText = true;
			setTimeout(() => { showSavedText = false; }, 2000);
			setTimeout(() => { if (usernameStatus === 'saved') usernameStatus = 'idle'; }, 2500);
		} catch (e: any) {
			usernameMsg = { type: 'error', text: e.detail || 'Failed to update username' };
			usernameStatus = 'error';
			setTimeout(() => { if (usernameStatus === 'error') usernameStatus = 'idle'; }, 2500);
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key === 's') {
			e.preventDefault();
			handleSaveUsername();
		}
	}

	async function handleChangePassword() {
		passwordMsg = null;
		if (newPassword !== confirmPassword) {
			passwordMsg = { type: 'error', text: 'Passwords do not match' };
			return;
		}
		if (!newPassword) {
			passwordMsg = { type: 'error', text: 'New password cannot be empty' };
			return;
		}
		savingPassword = true;
		try {
			await api.put('/api/auth/password', {
				current_password: currentPassword,
				new_password: newPassword
			});
			passwordMsg = { type: 'success', text: 'Password changed. Other sessions revoked.' };
			currentPassword = '';
			newPassword = '';
			confirmPassword = '';
		} catch (e: any) {
			passwordMsg = { type: 'error', text: e.detail || 'Failed to change password' };
		} finally {
			savingPassword = false;
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- Header bar -->
<div class="px-4 py-3 border-b border-base-300 shrink-0">
	<div class="flex items-center gap-2 h-8">
		<a href="{base}/settings" class="btn btn-ghost btn-sm btn-square md:hidden">
			<ChevronLeft size={18} />
		</a>
		<h2 class="font-semibold flex-1">Account</h2>
		<button
			class="btn btn-ghost btn-sm"
			onclick={handleSaveUsername}
			disabled={usernameStatus === 'saving'}
			title="Save username"
		>
			{#if usernameStatus === 'saving'}
				<span class="loading loading-spinner loading-xs"></span>
			{:else if usernameStatus === 'saved'}
				<Check size={16} class="text-success" />
				{#if showSavedText}
					<span class="text-xs text-success">Saved!</span>
				{/if}
			{:else if usernameStatus === 'error'}
				<Save size={16} class="text-error" />
			{:else}
				<Save size={16} />
			{/if}
		</button>
	</div>
</div>

<!-- Scrollable content -->
<div class="flex-1 overflow-y-auto p-4 md:p-6">
<div class="max-w-3xl flex flex-col gap-4">
	<!-- Username -->
	<div>
		<p class="text-sm font-medium mb-1">Username</p>
		<input
			type="text"
			class="input input-bordered input-sm w-full max-w-xs"
			bind:value={username}
		/>
		{#if usernameMsg}
			<p class="text-xs mt-1 {usernameMsg.type === 'success' ? 'text-success' : 'text-error'}">
				{usernameMsg.text}
			</p>
		{/if}
	</div>

	<!-- Password Change -->
	<div class="border-t border-base-300 pt-4 mt-4">
		<p class="text-sm font-medium mb-2">Change password</p>
		<div class="flex flex-col gap-2">
			<input
				type="password"
				class="input input-bordered input-sm w-full"
				placeholder="Current password"
				bind:value={currentPassword}
			/>
			<input
				type="password"
				class="input input-bordered input-sm w-full"
				placeholder="New password"
				bind:value={newPassword}
			/>
			<input
				type="password"
				class="input input-bordered input-sm w-full"
				placeholder="Confirm new password"
				bind:value={confirmPassword}
			/>
			<div>
				<Button variant="ghost" size="sm" loading={savingPassword} onclick={handleChangePassword}>
					Change Password
				</Button>
			</div>
			{#if passwordMsg}
				<p class="text-xs {passwordMsg.type === 'success' ? 'text-success' : 'text-error'}">
					{passwordMsg.text}
				</p>
			{/if}
		</div>
	</div>
</div>
</div>
