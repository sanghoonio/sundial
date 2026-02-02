<script lang="ts">
	import { api } from '$lib/services/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { UserResponse } from '$lib/types';
	import Button from '$lib/components/ui/Button.svelte';
	import { ChevronLeft } from 'lucide-svelte';

	let username = $state('');
	let savingUsername = $state(false);
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
		savingUsername = true;
		usernameMsg = null;
		try {
			await api.put<UserResponse>('/api/auth/username', { username });
			usernameMsg = { type: 'success', text: 'Username updated' };
		} catch (e: any) {
			usernameMsg = { type: 'error', text: e.detail || 'Failed to update username' };
		} finally {
			savingUsername = false;
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

<a href="/settings" class="btn btn-ghost btn-sm gap-1 mb-4 md:hidden">
	<ChevronLeft size={16} />
	Settings
</a>

<h2 class="font-semibold text-lg mb-4">Account</h2>

<div class="flex flex-col gap-6">
	<!-- Username -->
	<div>
		<p class="text-sm font-medium mb-1">Username</p>
		<div class="flex gap-2">
			<input
				type="text"
				class="input input-bordered input-sm flex-1"
				bind:value={username}
			/>
			<Button variant="ghost" size="sm" loading={savingUsername} onclick={handleSaveUsername}>
				Save
			</Button>
		</div>
		{#if usernameMsg}
			<p class="text-xs mt-1 {usernameMsg.type === 'success' ? 'text-success' : 'text-error'}">
				{usernameMsg.text}
			</p>
		{/if}
	</div>

	<!-- Password Change -->
	<div class="border-t border-base-300 pt-4">
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
