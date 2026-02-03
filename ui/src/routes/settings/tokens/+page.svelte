<script lang="ts">
	import { base } from '$app/paths';
	import { toast } from 'svelte-sonner';
	import { api } from '$lib/services/api';
	import type { TokenListItem, ApiKeyCreatedResponse, CreateApiKeyRequest } from '$lib/types';
	import Button from '$lib/components/ui/Button.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Modal from '$lib/components/ui/Modal.svelte';
	import { ChevronLeft, Copy, Check, Trash2 } from 'lucide-svelte';

	let tokens = $state<TokenListItem[]>([]);
	let loadingTokens = $state(true);
	let showCreateApiKey = $state(false);
	let newKeyName = $state('');
	let newKeyScope = $state('read_write');
	let creatingKey = $state(false);
	let createdKey = $state<ApiKeyCreatedResponse | null>(null);
	let copiedKey = $state(false);

	async function loadTokens() {
		loadingTokens = true;
		try {
			tokens = await api.get<TokenListItem[]>('/api/auth/tokens');
		} catch (e) {
			console.error('Failed to load tokens', e);
			toast.error('Failed to load tokens');
		} finally {
			loadingTokens = false;
		}
	}

	$effect(() => {
		loadTokens();
	});

	async function handleRevokeToken(tokenId: string) {
		try {
			await api.delete(`/api/auth/tokens/${tokenId}`);
			tokens = tokens.filter((t) => t.id !== tokenId);
		} catch (e: any) {
			console.error('Failed to revoke token', e);
			toast.error('Failed to revoke token');
		}
	}

	async function handleCreateApiKey() {
		creatingKey = true;
		try {
			const res = await api.post<ApiKeyCreatedResponse>('/api/auth/tokens', {
				name: newKeyName,
				scope: newKeyScope
			} as CreateApiKeyRequest);
			createdKey = res;
			loadTokens();
		} catch (e: any) {
			console.error('Failed to create API key', e);
			toast.error('Failed to create API key');
		} finally {
			creatingKey = false;
		}
	}

	function handleCloseCreateModal() {
		showCreateApiKey = false;
		createdKey = null;
		newKeyName = '';
		newKeyScope = 'read_write';
		copiedKey = false;
	}

	async function copyToken(token: string) {
		await navigator.clipboard.writeText(token);
		copiedKey = true;
	}

	function formatRelativeTime(iso: string | null): string {
		if (!iso) return 'Never';
		try {
			const date = new Date(iso);
			const now = new Date();
			const diffMs = now.getTime() - date.getTime();
			const diffMins = Math.floor(diffMs / 60000);
			if (diffMins < 1) return 'Just now';
			if (diffMins < 60) return `${diffMins}m ago`;
			const diffHours = Math.floor(diffMins / 60);
			if (diffHours < 24) return `${diffHours}h ago`;
			const diffDays = Math.floor(diffHours / 24);
			if (diffDays < 30) return `${diffDays}d ago`;
			return date.toLocaleDateString();
		} catch {
			return iso;
		}
	}

	function formatUserAgent(ua: string | null): string {
		if (!ua) return '';
		// Extract browser info from user agent
		if (ua.includes('Firefox/')) return 'Firefox';
		if (ua.includes('Edg/')) return 'Edge';
		if (ua.includes('Chrome/')) return 'Chrome';
		if (ua.includes('Safari/') && !ua.includes('Chrome')) return 'Safari';
		if (ua.includes('curl/')) return 'curl';
		// Truncate if unrecognized
		return ua.length > 20 ? ua.slice(0, 20) + '...' : ua;
	}
</script>

<!-- Header bar -->
<div class="px-4 py-3 border-b border-base-300 shrink-0">
	<div class="flex items-center gap-2 h-8">
		<a href="{base}/settings" class="btn btn-ghost btn-sm btn-square md:hidden">
			<ChevronLeft size={18} />
		</a>
		<h2 class="font-semibold">Sessions & API Keys</h2>
	</div>
</div>

<!-- Scrollable content -->
<div class="flex-1 overflow-y-auto p-4 md:p-6">
<div class="max-w-3xl flex flex-col gap-4">
	{#if loadingTokens}
		<span class="loading loading-spinner loading-sm"></span>
	{:else if tokens.length === 0}
		<p class="text-sm text-base-content/60">No active tokens</p>
	{:else}
		<div class="flex flex-col gap-2">
			{#each tokens as token}
				<div class="flex items-center justify-between gap-2 py-2 px-3 rounded-lg bg-base-200/50 text-sm">
					<div class="flex flex-col gap-0.5 min-w-0 flex-1">
						<div class="flex items-center gap-2 flex-wrap">
							<span class="font-medium truncate">{token.name || 'Unnamed'}</span>
							{#if token.is_current}
								<Badge variant="primary" class="badge-sm">Current</Badge>
							{/if}
							<Badge variant={token.token_type === 'api_key' ? 'accent' : 'ghost'} class="badge-sm">
								{token.token_type === 'api_key' ? 'API Key' : 'Session'}
							</Badge>
							{#if token.scope === 'read'}
								<Badge variant="info" class="badge-sm">Read Only</Badge>
							{/if}
						</div>
						<div class="text-xs text-base-content/50">
							Used {formatRelativeTime(token.last_used_at)} · Created {new Date(token.created_at).toLocaleDateString()}
							{#if token.ip_address || token.user_agent}
								<span class="text-base-content/40">
									{#if token.ip_address}· {token.ip_address}{/if}
									{#if token.user_agent} · {formatUserAgent(token.user_agent)}{/if}
								</span>
							{/if}
						</div>
					</div>
					{#if !token.is_current}
						<button
							class="btn btn-ghost btn-xs text-error"
							onclick={() => handleRevokeToken(token.id)}
							title="Revoke"
						>
							<Trash2 size={14} />
						</button>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
	<div>
		<Button variant="ghost" size="sm" onclick={() => { showCreateApiKey = true; }}>
			Create API Key
		</Button>
	</div>
</div>
</div>

<!-- Create API Key Modal -->
<Modal open={showCreateApiKey} title={createdKey ? 'API Key Created' : 'Create API Key'} onclose={handleCloseCreateModal}>
	{#if createdKey}
		<div class="flex flex-col gap-3">
			<p class="text-sm text-base-content/70">
				Copy this token now. You won't be able to see it again.
			</p>
			<div class="flex gap-2">
				<input
					type="text"
					class="input input-bordered input-sm flex-1 font-mono text-xs"
					value={createdKey.raw_token}
					readonly
				/>
				<button
					class="btn btn-sm btn-ghost"
					onclick={() => copyToken(createdKey!.raw_token)}
				>
					{#if copiedKey}
						<Check size={14} class="text-success" />
					{:else}
						<Copy size={14} />
					{/if}
				</button>
			</div>
			<div class="flex justify-end">
				<Button variant="ghost" size="sm" onclick={handleCloseCreateModal}>Done</Button>
			</div>
		</div>
	{:else}
		<div class="flex flex-col gap-3">
			<div>
				<p class="text-sm mb-1">Name</p>
				<input
					type="text"
					class="input input-bordered input-sm w-full"
					placeholder="e.g. MCP Server"
					bind:value={newKeyName}
				/>
			</div>
			<div>
				<p class="text-sm mb-1">Scope</p>
				<select class="select select-bordered select-sm w-full" bind:value={newKeyScope}>
					<option value="read_write">Read & Write</option>
					<option value="read">Read Only</option>
				</select>
			</div>
			<div class="flex justify-end gap-2">
				<Button variant="ghost" size="sm" onclick={handleCloseCreateModal}>Cancel</Button>
				<Button variant="primary" size="sm" loading={creatingKey} onclick={handleCreateApiKey}>
					Create
				</Button>
			</div>
		</div>
	{/if}
</Modal>
