<script lang="ts">
	import { api } from '$lib/services/api';
	import type {
		SettingsResponse,
		SettingsUpdate,
		CalendarSettingsResponse,
		CalendarSettingsUpdate,
		CalendarSyncResult,
		CalDAVCalendarInfo
	} from '$lib/types';
	import Card from '$lib/components/ui/Card.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import { Bot, Calendar, Palette, Save, RefreshCw, Check, AlertTriangle, Download, Upload, Database } from 'lucide-svelte';

	let settings = $state<SettingsResponse | null>(null);
	let calSettings = $state<CalendarSettingsResponse | null>(null);
	let loading = $state(true);
	let saving = $state(false);
	let syncing = $state(false);
	let testingConnection = $state(false);

	// General settings
	let aiEnabled = $state(false);
	let aiAutoTag = $state(true);
	let aiAutoExtractTasks = $state(true);
	let theme = $state('light');

	// Calendar settings
	let calendarSource = $state('');
	let calendarSyncEnabled = $state(false);
	let caldavServerUrl = $state('');
	let caldavUsername = $state('');
	let caldavPassword = $state('');
	let caldavHasPassword = $state(false);
	let selectedCalendars = $state<string[]>([]);
	let syncRangePastDays = $state(30);
	let syncRangeFutureDays = $state(90);
	let lastSyncAt = $state<string | null>(null);
	let lastSyncError = $state<string | null>(null);

	// CalDAV calendar list from test connection
	let availableCalendars = $state<CalDAVCalendarInfo[]>([]);

	// Workspace export/import
	let exporting = $state(false);
	let importing = $state(false);
	let importResult = $state<string | null>(null);
	let importFileInput = $state<HTMLInputElement>();

	async function loadSettings() {
		loading = true;
		try {
			const [res, calRes] = await Promise.all([
				api.get<SettingsResponse>('/api/settings'),
				api.get<CalendarSettingsResponse>('/api/calendar/settings')
			]);
			settings = res;
			calSettings = calRes;

			aiEnabled = res.ai_enabled;
			aiAutoTag = res.ai_auto_tag;
			aiAutoExtractTasks = res.ai_auto_extract_tasks;
			theme = res.theme;

			calendarSource = calRes.calendar_source;
			calendarSyncEnabled = calRes.sync_enabled;
			caldavServerUrl = calRes.caldav_server_url;
			caldavUsername = calRes.caldav_username;
			caldavHasPassword = calRes.caldav_has_password;
			selectedCalendars = calRes.selected_calendars;
			syncRangePastDays = calRes.sync_range_past_days;
			syncRangeFutureDays = calRes.sync_range_future_days;
			lastSyncAt = calRes.last_sync_at;
			lastSyncError = calRes.last_sync_error;
		} catch (e) {
			console.error('Failed to load settings', e);
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		loadSettings();
	});

	async function handleSave() {
		saving = true;
		try {
			// Save general settings
			const update: SettingsUpdate = {
				ai_enabled: aiEnabled,
				ai_auto_tag: aiAutoTag,
				ai_auto_extract_tasks: aiAutoExtractTasks,
				calendar_source: calendarSource,
				calendar_sync_enabled: calendarSyncEnabled,
				theme
			};
			settings = await api.put<SettingsResponse>('/api/settings', update);

			// Save calendar-specific settings
			const calUpdate: CalendarSettingsUpdate = {
				calendar_source: calendarSource,
				sync_enabled: calendarSyncEnabled,
				selected_calendars: selectedCalendars,
				sync_range_past_days: syncRangePastDays,
				sync_range_future_days: syncRangeFutureDays,
				caldav_server_url: caldavServerUrl,
				caldav_username: caldavUsername
			};
			// Only send password if user typed a new one
			if (caldavPassword) {
				calUpdate.caldav_password = caldavPassword;
			}
			calSettings = await api.put<CalendarSettingsResponse>('/api/calendar/settings', calUpdate);
			caldavHasPassword = calSettings.caldav_has_password;
			caldavPassword = '';

			document.documentElement.setAttribute('data-theme', theme);
		} catch (e) {
			console.error('Failed to save settings', e);
		} finally {
			saving = false;
		}
	}

	async function handleTestConnection() {
		testingConnection = true;
		try {
			// Save credentials first so the server has them
			const calUpdate: CalendarSettingsUpdate = {
				caldav_server_url: caldavServerUrl,
				caldav_username: caldavUsername
			};
			if (caldavPassword) {
				calUpdate.caldav_password = caldavPassword;
			}
			await api.put<CalendarSettingsResponse>('/api/calendar/settings', calUpdate);

			const calendars = await api.get<CalDAVCalendarInfo[]>('/api/calendar/caldav/calendars');
			availableCalendars = calendars;
		} catch (e: unknown) {
			console.error('Calendar connection failed', e);
			availableCalendars = [];
		} finally {
			testingConnection = false;
		}
	}

	async function handleCalendarSync() {
		syncing = true;
		try {
			const result = await api.post<CalendarSyncResult>('/api/calendar/sync');
			lastSyncAt = result.last_sync;
			if (result.errors.length > 0) {
				lastSyncError = result.errors[0];
			} else {
				lastSyncError = null;
			}
		} catch (e) {
			console.error('Calendar sync failed', e);
		} finally {
			syncing = false;
		}
	}

	function toggleCalendarSelection(calId: string) {
		if (selectedCalendars.includes(calId)) {
			selectedCalendars = selectedCalendars.filter((c) => c !== calId);
		} else {
			selectedCalendars = [...selectedCalendars, calId];
		}
	}

	function formatSyncTime(iso: string | null): string {
		if (!iso) return 'Never';
		try {
			return new Date(iso).toLocaleString();
		} catch {
			return iso;
		}
	}

	async function handleExportWorkspace() {
		exporting = true;
		try {
			const res = await fetch('/api/export/workspace', {
				headers: api.authHeaders()
			});
			if (!res.ok) throw new Error('Export failed');
			const blob = await res.blob();
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = 'sundial-backup.zip';
			document.body.appendChild(a);
			a.click();
			document.body.removeChild(a);
			URL.revokeObjectURL(url);
		} catch (e) {
			console.error('Failed to export workspace', e);
		} finally {
			exporting = false;
		}
	}

	async function handleImportWorkspace(e: Event) {
		const input = e.target as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;

		if (!confirm('This will replace ALL existing data with the backup. Continue?')) {
			input.value = '';
			return;
		}

		importing = true;
		importResult = null;
		try {
			const formData = new FormData();
			formData.append('file', file);
			const res = await fetch('/api/import/workspace', {
				method: 'POST',
				headers: api.authHeaders(),
				body: formData
			});
			const result = await res.json();
			if (result.error) {
				importResult = `Error: ${result.error}`;
			} else {
				const total = Object.values(result.restored as Record<string, number>).reduce((a: number, b: number) => a + b, 0);
				importResult = `Restored ${total} records and ${result.files} files`;
				// Reload settings since they were restored
				loadSettings();
			}
		} catch (e) {
			console.error('Failed to import workspace', e);
			importResult = 'Import failed';
		} finally {
			importing = false;
			input.value = '';
		}
	}
</script>

{#if loading}
	<div class="flex items-center justify-center py-20">
		<span class="loading loading-spinner loading-lg"></span>
	</div>
{:else}
	<div class="max-w-2xl mx-auto flex flex-col gap-6">
		<!-- AI Settings -->
		<Card>
			<h2 class="font-semibold flex items-center gap-2 mb-4">
				<Bot size={18} />
				AI Features
			</h2>
			<div class="flex flex-col gap-3">
				<label class="flex items-center justify-between cursor-pointer">
					<div>
						<p class="font-medium text-sm">Enable AI</p>
						<p class="text-xs text-base-content/60">Use Claude for auto-tagging and task extraction</p>
					</div>
					<input type="checkbox" class="toggle toggle-primary" bind:checked={aiEnabled} />
				</label>

				{#if aiEnabled}
					<label class="flex items-center justify-between cursor-pointer pl-4">
						<div>
							<p class="font-medium text-sm">Auto-tag notes</p>
							<p class="text-xs text-base-content/60">Automatically suggest tags for new notes</p>
						</div>
						<input type="checkbox" class="toggle toggle-sm" bind:checked={aiAutoTag} />
					</label>

					<label class="flex items-center justify-between cursor-pointer pl-4">
						<div>
							<p class="font-medium text-sm">Extract tasks</p>
							<p class="text-xs text-base-content/60">
								Automatically detect actionable items in notes
							</p>
						</div>
						<input type="checkbox" class="toggle toggle-sm" bind:checked={aiAutoExtractTasks} />
					</label>
				{/if}
			</div>
		</Card>

		<!-- Calendar Settings -->
		<Card>
			<h2 class="font-semibold flex items-center gap-2 mb-4">
				<Calendar size={18} />
				Calendar
			</h2>
			<div class="flex flex-col gap-4">
				<div>
					<p class="text-sm font-medium mb-1">Calendar source</p>
					<select
						class="select select-bordered select-sm w-full max-w-xs"
						bind:value={calendarSource}
					>
						<option value="">None (local only)</option>
						<option value="caldav">CalDAV (iCloud, Fastmail, Nextcloud, etc.)</option>
					</select>
				</div>

				{#if calendarSource === 'caldav'}
					<div class="flex flex-col gap-3 pl-3 border-l-2 border-base-300 ml-1">
						<div>
							<p class="text-sm mb-1">Server URL</p>
							<input
								type="url"
								class="input input-bordered input-sm w-full"
								placeholder="https://pXX-caldav.icloud.com/USERID/calendars/"
								bind:value={caldavServerUrl}
							/>
						</div>

						<div>
							<p class="text-sm mb-1">Username</p>
							<input
								type="text"
								class="input input-bordered input-sm w-full"
								placeholder="you@icloud.com"
								bind:value={caldavUsername}
							/>
						</div>

						<div>
							<p class="text-sm mb-1">App-specific password</p>
							<input
								type="password"
								class="input input-bordered input-sm w-full"
								placeholder={caldavHasPassword ? '********' : 'Enter password'}
								bind:value={caldavPassword}
							/>
							{#if caldavHasPassword && !caldavPassword}
								<p class="text-xs text-success mt-1 flex items-center gap-1">
									<Check size={12} /> Password saved
								</p>
							{/if}
						</div>

						<div>
							<Button
								variant="ghost"
								size="sm"
								loading={testingConnection}
								onclick={handleTestConnection}
							>
								Test Connection
							</Button>
						</div>

						{#if availableCalendars.length > 0}
							<div>
								<p class="text-sm font-medium mb-2">Select calendars to sync:</p>
								<div class="flex flex-col gap-1">
									{#each availableCalendars as cal}
										<label class="flex items-center gap-2 cursor-pointer py-1">
											<input
												type="checkbox"
												class="checkbox checkbox-sm"
												checked={selectedCalendars.includes(cal.id)}
												onchange={() => toggleCalendarSelection(cal.id)}
											/>
											<span
												class="inline-block w-3 h-3 rounded-full flex-shrink-0"
												style:background-color={cal.color || '#6b7280'}
											></span>
											<span class="text-sm">{cal.name}</span>
										</label>
									{/each}
								</div>
							</div>
						{/if}

						<div class="grid grid-cols-2 gap-3">
							<div>
								<p class="text-sm mb-1">Sync past (days)</p>
								<input
									type="number"
									class="input input-bordered input-sm w-full"
									min="1"
									max="365"
									bind:value={syncRangePastDays}
								/>
							</div>
							<div>
								<p class="text-sm mb-1">Sync future (days)</p>
								<input
									type="number"
									class="input input-bordered input-sm w-full"
									min="1"
									max="365"
									bind:value={syncRangeFutureDays}
								/>
							</div>
						</div>
					</div>
				{/if}

				<label class="flex items-center justify-between cursor-pointer">
					<div>
						<p class="font-medium text-sm">Calendar sync</p>
						<p class="text-xs text-base-content/60">Periodically sync events from your calendar</p>
					</div>
					<input type="checkbox" class="toggle toggle-primary" bind:checked={calendarSyncEnabled} />
				</label>

				{#if calendarSyncEnabled && calendarSource === 'caldav'}
					<div class="flex items-center gap-3">
						<Button variant="ghost" size="sm" loading={syncing} onclick={handleCalendarSync}>
							<RefreshCw size={14} />
							Sync now
						</Button>
						<span class="text-xs text-base-content/60">
							Last sync: {formatSyncTime(lastSyncAt)}
						</span>
					</div>

					{#if lastSyncError}
						<div class="flex items-start gap-2 text-xs text-warning">
							<AlertTriangle size={14} class="flex-shrink-0 mt-0.5" />
							<span>{lastSyncError}</span>
						</div>
					{/if}
				{/if}
			</div>
		</Card>

		<!-- Appearance -->
		<Card>
			<h2 class="font-semibold flex items-center gap-2 mb-4">
				<Palette size={18} />
				Appearance
			</h2>
			<div>
				<p class="text-sm font-medium mb-1">Theme</p>
				<select class="select select-bordered select-sm w-full max-w-xs" bind:value={theme}>
					<option value="light">Light</option>
					<option value="dark">Dark</option>
				</select>
			</div>
		</Card>

		<!-- Data -->
		<Card>
			<h2 class="font-semibold flex items-center gap-2 mb-4">
				<Database size={18} />
				Data
			</h2>
			<div class="flex flex-col gap-4">
				<div>
					<p class="text-sm font-medium mb-1">Export workspace</p>
					<p class="text-xs text-base-content/60 mb-2">Download all notes, tasks, projects, and settings as a ZIP file</p>
					<Button variant="ghost" size="sm" loading={exporting} onclick={handleExportWorkspace}>
						<Download size={14} />
						Export Workspace
					</Button>
				</div>
				<div class="border-t border-base-300 pt-4">
					<p class="text-sm font-medium mb-1">Restore from backup</p>
					<p class="text-xs text-base-content/60 mb-2">Upload a previously exported ZIP to restore all data</p>
					<input
						type="file"
						accept=".zip"
						class="hidden"
						bind:this={importFileInput}
						onchange={handleImportWorkspace}
					/>
					<Button
						variant="ghost"
						size="sm"
						loading={importing}
						onclick={() => importFileInput?.click()}
					>
						<Upload size={14} />
						Restore from Backup
					</Button>
					{#if importResult}
						<p class="text-xs mt-2 {importResult.startsWith('Error') ? 'text-error' : 'text-success'}">
							{importResult}
						</p>
					{/if}
				</div>
			</div>
		</Card>

		<!-- Save -->
		<div class="sticky bottom-0 py-4 bg-base-100 border-t border-base-300 -mx-4 px-4 flex items-center">
			<Button variant="primary" loading={saving} onclick={handleSave}>
				<Save size={16} />
				Save Settings
			</Button>
		</div>
	</div>
{/if}
