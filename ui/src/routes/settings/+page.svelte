<script lang="ts">
	import { api } from '$lib/services/api';
	import { toasts } from '$lib/stores/toasts.svelte';
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
	import { Bot, Calendar, Palette, Save, RefreshCw, Check, AlertTriangle } from 'lucide-svelte';

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
		} catch {
			toasts.error('Failed to load settings');
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

			toasts.success('Settings saved');
			document.documentElement.setAttribute('data-theme', theme);
		} catch {
			toasts.error('Failed to save settings');
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
			toasts.success(`Found ${calendars.length} calendar(s)`);
		} catch (e: unknown) {
			const msg = e instanceof Error ? e.message : 'Connection failed';
			toasts.error(msg);
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
				toasts.error(`Sync completed with errors: ${result.errors[0]}`);
			} else {
				lastSyncError = null;
				toasts.success(
					`Synced: ${result.created} created, ${result.updated} updated, ${result.deleted} deleted`
				);
			}
		} catch {
			toasts.error('Calendar sync failed');
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
					<!-- svelte-ignore a11y_label_has_associated_control -->
					<label class="label"
						><span class="label-text text-sm font-medium">Calendar source</span></label
					>
					<select
						class="select select-bordered select-sm w-full max-w-xs"
						bind:value={calendarSource}
					>
						<option value="">None (local only)</option>
						<option value="caldav">CalDAV (iCloud, Fastmail, Nextcloud, etc.)</option>
					</select>
				</div>

				{#if calendarSource === 'caldav'}
					<div class="flex flex-col gap-3 pl-2 border-l-2 border-base-300 ml-1">
						<div>
							<!-- svelte-ignore a11y_label_has_associated_control -->
							<label class="label"
								><span class="label-text text-sm">Server URL</span></label
							>
							<input
								type="url"
								class="input input-bordered input-sm w-full"
								placeholder="https://pXX-caldav.icloud.com/USERID/calendars/"
								bind:value={caldavServerUrl}
							/>
						</div>

						<div>
							<!-- svelte-ignore a11y_label_has_associated_control -->
							<label class="label"><span class="label-text text-sm">Username</span></label>
							<input
								type="text"
								class="input input-bordered input-sm w-full"
								placeholder="you@icloud.com"
								bind:value={caldavUsername}
							/>
						</div>

						<div>
							<!-- svelte-ignore a11y_label_has_associated_control -->
							<label class="label"
								><span class="label-text text-sm">App-specific password</span></label
							>
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
								<!-- svelte-ignore a11y_label_has_associated_control -->
								<label class="label"
									><span class="label-text text-sm">Sync past (days)</span></label
								>
								<input
									type="number"
									class="input input-bordered input-sm w-full"
									min="1"
									max="365"
									bind:value={syncRangePastDays}
								/>
							</div>
							<div>
								<!-- svelte-ignore a11y_label_has_associated_control -->
								<label class="label"
									><span class="label-text text-sm">Sync future (days)</span></label
								>
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
				<!-- svelte-ignore a11y_label_has_associated_control -->
				<label class="label"><span class="label-text text-sm font-medium">Theme</span></label>
				<select class="select select-bordered select-sm w-full max-w-xs" bind:value={theme}>
					<option value="light">Light</option>
					<option value="dark">Dark</option>
				</select>
			</div>
		</Card>

		<!-- Save -->
		<div class="flex items-center gap-2">
			<Button variant="primary" loading={saving} onclick={handleSave}>
				<Save size={16} />
				Save Settings
			</Button>
		</div>
	</div>
{/if}
