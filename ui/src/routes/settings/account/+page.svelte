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
			const updated = await api.put<UserResponse>('/api/auth/username', { username });
			auth.setUser(updated);
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

<!-- Header bar -->
<div class="px-4 py-3 border-b border-base-300 shrink-0">
	<div class="flex items-center gap-2 h-8">
		<a href="/settings" class="btn btn-ghost btn-sm btn-square md:hidden">
			<ChevronLeft size={18} />
		</a>
		<h2 class="font-semibold">Account</h2>
	</div>
</div>

<!-- Scrollable content -->
<div class="flex-1 overflow-y-auto p-4 md:p-6">
<div class="max-w-3xl flex flex-col gap-4">
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
