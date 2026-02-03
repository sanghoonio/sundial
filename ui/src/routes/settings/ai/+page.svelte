<script lang="ts">
	import { base } from '$app/paths';
	import { toast } from 'svelte-sonner';
	import { api } from '$lib/services/api';
	import type { SettingsResponse, SettingsUpdate } from '$lib/types';
	import { ChevronLeft, Save, Check, CheckCircle, XCircle, Copy } from 'lucide-svelte';

	let loading = $state(true);
	let saveStatus: 'idle' | 'saving' | 'saved' | 'error' = $state('idle');
	let showSavedText = $state(false);
	let aiEnabled = $state(false);
	let aiAutoTag = $state(true);
	let aiAutoExtractTasks = $state(true);
	let aiAutoLinkEvents = $state(true);
	let aiDailySuggestions = $state(true);
	let aiProvider = $state('openrouter');
	let openrouterApiKey = $state('');
	let openrouterApiKeyOriginal = $state('');
	let openrouterModel = $state('anthropic/claude-sonnet-4');
	let nvidiaApiKey = $state('');
	let nvidiaApiKeyOriginal = $state('');
	let nvidiaModel = $state('nvidia/llama-3.1-nemotron-70b-instruct');
	let mcpEnabled = $state(true);
	let copiedConfig = $state(false);

	let hasOpenrouterKey = $derived(openrouterApiKey.length > 0 && openrouterApiKey !== '');
	let hasNvidiaKey = $derived(nvidiaApiKey.length > 0 && nvidiaApiKey !== '');

	let mcpUrl = $derived(typeof window !== 'undefined' ? `${window.location.origin}/mcp/sse` : '');
	let mcpConfig = $derived(JSON.stringify({
		mcpServers: {
			sundial: {
				url: mcpUrl,
				headers: {
					Authorization: 'Bearer YOUR_API_TOKEN'
				}
			}
		}
	}, null, 2));

	async function copyMcpConfig() {
		await navigator.clipboard.writeText(mcpConfig);
		copiedConfig = true;
		setTimeout(() => { copiedConfig = false; }, 2000);
	}

	async function loadSettings() {
		loading = true;
		try {
			const res = await api.get<SettingsResponse>('/api/settings');
			aiEnabled = res.ai_enabled;
			aiAutoTag = res.ai_auto_tag;
			aiAutoExtractTasks = res.ai_auto_extract_tasks;
			aiAutoLinkEvents = res.ai_auto_link_events;
			aiDailySuggestions = res.ai_daily_suggestions;
			aiProvider = res.ai_provider;
			openrouterApiKey = res.openrouter_api_key;
			openrouterApiKeyOriginal = res.openrouter_api_key;
			openrouterModel = res.openrouter_model;
			nvidiaApiKey = res.nvidia_api_key;
			nvidiaApiKeyOriginal = res.nvidia_api_key;
			nvidiaModel = res.nvidia_model;
			mcpEnabled = res.mcp_enabled;
		} catch (e) {
			console.error('Failed to load settings', e);
			toast.error('Failed to load AI settings');
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		loadSettings();
	});

	async function handleSave() {
		saveStatus = 'saving';
		try {
			const update: SettingsUpdate = {
				ai_enabled: aiEnabled,
				ai_auto_tag: aiAutoTag,
				ai_auto_extract_tasks: aiAutoExtractTasks,
				ai_auto_link_events: aiAutoLinkEvents,
				ai_daily_suggestions: aiDailySuggestions,
				ai_provider: aiProvider,
				openrouter_model: openrouterModel,
				nvidia_model: nvidiaModel,
				mcp_enabled: mcpEnabled
			};
			// Only send API keys if changed (not the masked value)
			if (openrouterApiKey !== openrouterApiKeyOriginal) {
				update.openrouter_api_key = openrouterApiKey;
			}
			if (nvidiaApiKey !== nvidiaApiKeyOriginal) {
				update.nvidia_api_key = nvidiaApiKey;
			}
			const res = await api.put<SettingsResponse>('/api/settings', update);
			aiEnabled = res.ai_enabled;
			aiAutoTag = res.ai_auto_tag;
			aiAutoExtractTasks = res.ai_auto_extract_tasks;
			aiAutoLinkEvents = res.ai_auto_link_events;
			aiDailySuggestions = res.ai_daily_suggestions;
			aiProvider = res.ai_provider;
			openrouterApiKey = res.openrouter_api_key;
			openrouterApiKeyOriginal = res.openrouter_api_key;
			openrouterModel = res.openrouter_model;
			nvidiaApiKey = res.nvidia_api_key;
			nvidiaApiKeyOriginal = res.nvidia_api_key;
			nvidiaModel = res.nvidia_model;
			mcpEnabled = res.mcp_enabled;
			saveStatus = 'saved';
			showSavedText = true;
			setTimeout(() => { showSavedText = false; }, 2000);
			setTimeout(() => { if (saveStatus === 'saved') saveStatus = 'idle'; }, 2500);
		} catch (e) {
			console.error('Failed to save AI settings', e);
			toast.error('Failed to save AI settings');
			saveStatus = 'error';
			setTimeout(() => { if (saveStatus === 'error') saveStatus = 'idle'; }, 2500);
		}
	}
	function handleKeydown(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key === 's') {
			e.preventDefault();
			handleSave();
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
		<h2 class="font-semibold flex-1">AI Features</h2>
		<button
			class="btn btn-ghost btn-sm"
			onclick={handleSave}
			disabled={saveStatus === 'saving'}
			title="Save"
		>
			{#if saveStatus === 'saving'}
				<span class="loading loading-spinner loading-xs"></span>
			{:else if saveStatus === 'saved'}
				<Check size={16} class="text-success" />
				{#if showSavedText}
					<span class="text-xs text-success">Saved!</span>
				{/if}
			{:else if saveStatus === 'error'}
				<Save size={16} class="text-error" />
			{:else}
				<Save size={16} />
			{/if}
		</button>
	</div>
</div>

<!-- Scrollable content -->
<div class="flex-1 overflow-y-auto p-4 md:p-6">
<div class="max-w-3xl">
{#if loading}
	<div class="flex items-center justify-center py-10">
		<span class="loading loading-spinner loading-md"></span>
	</div>
{:else}
	<div class="flex flex-col gap-4">
		<label class="flex items-center justify-between cursor-pointer">
			<div>
				<p class="font-medium text-sm">Enable AI</p>
				<p class="text-xs text-base-content/60">Use AI for auto-tagging, task extraction, and chat</p>
			</div>
			<input type="checkbox" class="toggle toggle-primary" bind:checked={aiEnabled} />
		</label>

		{#if aiEnabled}
			<div class="border-t border-base-300 pt-4 mt-4"></div>

			<div class="flex flex-col gap-1">
				<p class="font-medium text-sm">AI Provider</p>
				<div class="flex gap-4">
					<label class="flex items-center gap-2 cursor-pointer">
						<input type="radio" value="openrouter" bind:group={aiProvider} class="radio radio-sm" />
						<span class="text-sm">OpenRouter</span>
					</label>
					<label class="flex items-center gap-2 cursor-pointer">
						<input type="radio" value="nvidia" bind:group={aiProvider} class="radio radio-sm" />
						<span class="text-sm">NVIDIA</span>
					</label>
				</div>
			</div>

			{#if aiProvider === 'openrouter'}
				<div class="flex flex-col gap-1">
					<label class="font-medium text-sm" for="openrouter-api-key">OpenRouter API Key</label>
					<div class="flex items-center gap-2">
						<input
							id="openrouter-api-key"
							type="password"
							class="input input-bordered input-sm flex-1"
							placeholder="sk-or-..."
							bind:value={openrouterApiKey}
						/>
						{#if hasOpenrouterKey}
							<span class="text-success flex items-center gap-1 text-xs">
								<CheckCircle size={14} />
								Configured
							</span>
						{:else}
							<span class="text-warning flex items-center gap-1 text-xs">
								<XCircle size={14} />
								Not set
							</span>
						{/if}
					</div>
					<p class="text-xs text-base-content/50">
						Get an API key from <a href="https://openrouter.ai/keys" target="_blank" class="link">openrouter.ai/keys</a>
					</p>
				</div>

				<div class="flex flex-col gap-1">
					<label class="font-medium text-sm" for="openrouter-model">Model</label>
					<input
						id="openrouter-model"
						type="text"
						class="input input-bordered input-sm"
						placeholder="anthropic/claude-sonnet-4"
						bind:value={openrouterModel}
					/>
					<p class="text-xs text-base-content/50">
						OpenRouter model ID. Browse models at <a href="https://openrouter.ai/models" target="_blank" class="link">openrouter.ai/models</a>
					</p>
				</div>
			{:else}
				<div class="flex flex-col gap-1">
					<label class="font-medium text-sm" for="nvidia-api-key">NVIDIA API Key</label>
					<div class="flex items-center gap-2">
						<input
							id="nvidia-api-key"
							type="password"
							class="input input-bordered input-sm flex-1"
							placeholder="nvapi-..."
							bind:value={nvidiaApiKey}
						/>
						{#if hasNvidiaKey}
							<span class="text-success flex items-center gap-1 text-xs">
								<CheckCircle size={14} />
								Configured
							</span>
						{:else}
							<span class="text-warning flex items-center gap-1 text-xs">
								<XCircle size={14} />
								Not set
							</span>
						{/if}
					</div>
					<p class="text-xs text-base-content/50">
						Get an API key from <a href="https://build.nvidia.com" target="_blank" class="link">build.nvidia.com</a>
					</p>
				</div>

				<div class="flex flex-col gap-1">
					<label class="font-medium text-sm" for="nvidia-model">Model</label>
					<input
						id="nvidia-model"
						type="text"
						class="input input-bordered input-sm"
						placeholder="nvidia/llama-3.1-nemotron-70b-instruct"
						bind:value={nvidiaModel}
					/>
					<p class="text-xs text-base-content/50">
						NVIDIA model ID. Browse models at <a href="https://build.nvidia.com/models" target="_blank" class="link">build.nvidia.com/models</a>
					</p>
				</div>
			{/if}

			<div class="border-t border-base-300 pt-4 mt-2">
				<p class="text-xs font-medium text-base-content/50 mb-3">Background Processing</p>
			</div>

			<label class="flex items-center justify-between cursor-pointer">
				<div>
					<p class="font-medium text-sm">Auto-tag notes</p>
					<p class="text-xs text-base-content/60">Automatically suggest tags when saving notes</p>
				</div>
				<input type="checkbox" class="toggle toggle-sm" bind:checked={aiAutoTag} />
			</label>

			<label class="flex items-center justify-between cursor-pointer">
				<div>
					<p class="font-medium text-sm">Extract tasks</p>
					<p class="text-xs text-base-content/60">Automatically detect actionable items in notes</p>
				</div>
				<input type="checkbox" class="toggle toggle-sm" bind:checked={aiAutoExtractTasks} />
			</label>

			<label class="flex items-center justify-between cursor-pointer">
				<div>
					<p class="font-medium text-sm">Link calendar events</p>
					<p class="text-xs text-base-content/60">Automatically link notes to related calendar events</p>
				</div>
				<input type="checkbox" class="toggle toggle-sm" bind:checked={aiAutoLinkEvents} />
			</label>

			<div class="border-t border-base-300 pt-4 mt-2">
				<p class="text-xs font-medium text-base-content/50 mb-3">Dashboard</p>
			</div>

			<label class="flex items-center justify-between cursor-pointer">
				<div>
					<p class="font-medium text-sm">Daily suggestions</p>
					<p class="text-xs text-base-content/60">Show AI insights on the dashboard</p>
				</div>
				<input type="checkbox" class="toggle toggle-sm" bind:checked={aiDailySuggestions} />
			</label>
		{/if}

		<!-- MCP Section -->
		<div class="border-t border-base-300 pt-4 mt-4">
			<p class="text-xs font-medium text-base-content/50 mb-3">MCP (Model Context Protocol)</p>
		</div>

		<label class="flex items-center justify-between cursor-pointer">
			<div>
				<p class="font-medium text-sm">Enable MCP Server</p>
				<p class="text-xs text-base-content/60">Allow external AI clients like Claude Desktop to access your data</p>
			</div>
			<input type="checkbox" class="toggle toggle-sm" bind:checked={mcpEnabled} />
		</label>

		{#if mcpEnabled}
			<div class="flex flex-col gap-3 mt-2 p-4 bg-base-200/50 rounded-lg">
				<div>
					<p class="font-medium text-sm mb-1">Setup Instructions</p>
					<p class="text-xs text-base-content/60 mb-2">
						To use Sundial with Claude Desktop, add this to your config file:
					</p>
					<ul class="text-xs text-base-content/60 list-disc list-inside mb-2">
						<li><strong>macOS:</strong> ~/Library/Application Support/Claude/claude_desktop_config.json</li>
						<li><strong>Windows:</strong> %APPDATA%\Claude\claude_desktop_config.json</li>
					</ul>
				</div>

				<div class="flex flex-col gap-1">
					<div class="flex items-center justify-between">
						<p class="text-xs text-base-content/60">Configuration:</p>
						<button
							class="btn btn-ghost btn-xs gap-1"
							onclick={copyMcpConfig}
						>
							{#if copiedConfig}
								<Check size={12} class="text-success" />
								<span class="text-success">Copied!</span>
							{:else}
								<Copy size={12} />
								Copy
							{/if}
						</button>
					</div>
					<pre class="text-xs bg-base-300 p-3 rounded overflow-x-auto font-mono">{mcpConfig}</pre>
				</div>

				<div class="text-xs text-base-content/60">
					<p class="mb-1"><strong>Steps:</strong></p>
					<ol class="list-decimal list-inside space-y-1">
						<li>Create an API token in <a href="{base}/settings/tokens" class="link">Settings → Tokens</a></li>
						<li>Replace <code class="bg-base-300 px-1 rounded">YOUR_API_TOKEN</code> with your token</li>
						<li>Save the config file and restart Claude Desktop</li>
					</ol>
				</div>

				<p class="text-xs text-base-content/50 mt-1">
					The MCP server exposes 12 tools: search/list/create/update notes, list/create/update tasks, list projects, list tags, calendar events, and dashboard.
				</p>
			</div>
		{/if}
	</div>
{/if}
</div>
</div>
