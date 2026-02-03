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
	import Button from '$lib/components/ui/Button.svelte';
	import { ChevronLeft, Save, RefreshCw, Check, AlertTriangle } from 'lucide-svelte';

	let loading = $state(true);
	let saving = $state(false);
	let syncing = $state(false);
	let testingConnection = $state(false);

	let calendarSource = $state('');
	let calendarSyncEnabled = $state(false);
	let caldavServerUrl = $state('');
	let caldavUsername = $state('');
	let caldavPassword = $state('');
	let caldavHasPassword = $state(false);
	let selectedCalendars = $state<string[]>([]);
	let syncRangePastDays = $state(30);
	let syncRangeFutureDays = $state(90);
	let syncIntervalMinutes = $state(0);
	let syncDirection = $state('import');
	let lastSyncAt = $state<string | null>(null);
	let lastSyncError = $state<string | null>(null);
	let availableCalendars = $state<CalDAVCalendarInfo[]>([]);

	async function loadSettings() {
		loading = true;
		try {
			const [general, cal] = await Promise.all([
				api.get<SettingsResponse>('/api/settings'),
				api.get<CalendarSettingsResponse>('/api/calendar/settings')
			]);

			calendarSource = cal.calendar_source;
			calendarSyncEnabled = cal.sync_enabled;
			caldavServerUrl = cal.caldav_server_url;
			caldavUsername = cal.caldav_username;
			caldavHasPassword = cal.caldav_has_password;
			selectedCalendars = cal.selected_calendars;
			syncRangePastDays = cal.sync_range_past_days;
			syncRangeFutureDays = cal.sync_range_future_days;
			syncIntervalMinutes = cal.sync_interval_minutes;
			syncDirection = cal.sync_direction || 'both';
			lastSyncAt = cal.last_sync_at;
			lastSyncError = cal.last_sync_error;
		} catch (e) {
			console.error('Failed to load calendar settings', e);
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
			// Save general settings (calendar_source, calendar_sync_enabled)
			const generalUpdate: SettingsUpdate = {
				calendar_source: calendarSource,
				calendar_sync_enabled: calendarSyncEnabled
			};
			await api.put<SettingsResponse>('/api/settings', generalUpdate);

			// Save calendar-specific settings
			const calUpdate: CalendarSettingsUpdate = {
				calendar_source: calendarSource,
				sync_enabled: calendarSyncEnabled,
				selected_calendars: selectedCalendars,
				sync_range_past_days: syncRangePastDays,
				sync_range_future_days: syncRangeFutureDays,
				sync_interval_minutes: syncIntervalMinutes,
				sync_direction: syncDirection,
				caldav_server_url: caldavServerUrl,
				caldav_username: caldavUsername
			};
			if (caldavPassword) {
				calUpdate.caldav_password = caldavPassword;
			}
			const calRes = await api.put<CalendarSettingsResponse>('/api/calendar/settings', calUpdate);
			caldavHasPassword = calRes.caldav_has_password;
			caldavPassword = '';
		} catch (e) {
			console.error('Failed to save calendar settings', e);
		} finally {
			saving = false;
		}
	}

	async function handleTestConnection() {
		testingConnection = true;
		try {
			const calUpdate: CalendarSettingsUpdate = {
				calendar_source: calendarSource,
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
</script>

<!-- Header bar -->
<div class="px-4 py-3 border-b border-base-300 shrink-0">
	<div class="flex items-center gap-2 h-8">
		<a href="/settings" class="btn btn-ghost btn-sm btn-square md:hidden">
			<ChevronLeft size={18} />
		</a>
		<h2 class="font-semibold">Calendar</h2>
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
			<!-- Connection -->
			<div class="flex flex-col gap-3">
				<p class="text-xs font-semibold text-base-content/50 uppercase tracking-wide">Connection</p>
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
			</div>

			<!-- Calendars -->
			{#if availableCalendars.length > 0}
				<div class="flex flex-col gap-2">
					<p class="text-xs font-semibold text-base-content/50 uppercase tracking-wide">Calendars</p>
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

			<!-- Sync Options -->
			<div class="flex flex-col gap-3">
				<p class="text-xs font-semibold text-base-content/50 uppercase tracking-wide">Sync Options</p>

				<label class="flex items-center justify-between cursor-pointer">
					<div>
						<p class="font-medium text-sm">Enable sync</p>
						<p class="text-xs text-base-content/60">Sync events between Sundial and your CalDAV server</p>
					</div>
					<input type="checkbox" class="toggle toggle-primary" bind:checked={calendarSyncEnabled} />
				</label>

				{#if calendarSyncEnabled}
					<div>
						<p class="text-sm mb-1">Sync direction</p>
						<select
							class="select select-bordered select-sm w-full max-w-xs"
							bind:value={syncDirection}
						>
							<option value="import">Import only (read from server)</option>
							<option value="export">Export only (write to server)</option>
							<option value="both">Two-way (import & export)</option>
						</select>
						<p class="text-xs text-base-content/50 mt-1">
							Import pulls events from your CalDAV server. Export pushes local changes to it.
						</p>
					</div>

					<div>
						<p class="text-sm mb-1">Sync frequency</p>
						<select
							class="select select-bordered select-sm w-full max-w-xs"
							bind:value={syncIntervalMinutes}
						>
							<option value={0}>Manual only</option>
							<option value={15}>Every 15 minutes</option>
							<option value={30}>Every 30 minutes</option>
							<option value={60}>Every hour</option>
							<option value={360}>Every 6 hours</option>
						</select>
						<p class="text-xs text-base-content/50 mt-1">
							Automatic sync runs while the calendar page is open
						</p>
					</div>

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
		{/if}

		<div class="pt-2">
			<Button variant="primary" size="sm" loading={saving} onclick={handleSave}>
				<Save size={14} />
				Save
			</Button>
		</div>
	</div>
{/if}
</div>
</div>
