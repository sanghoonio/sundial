<script lang="ts">
	import { api } from '$lib/services/api';
	import Button from '$lib/components/ui/Button.svelte';
	import { ChevronLeft, Download, Upload } from 'lucide-svelte';
	import { confirmModal } from '$lib/stores/confirm.svelte';

	let exporting = $state(false);
	let importing = $state(false);
	let importResult = $state<string | null>(null);
	let importFileInput = $state<HTMLInputElement>();

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

		const confirmed = await confirmModal.confirm({
			title: 'Replace Data',
			message: 'This will replace ALL existing data with the backup. Continue?',
			confirmText: 'Replace',
			variant: 'warning'
		});
		if (!confirmed) {
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

<!-- Header bar -->
<div class="px-4 py-3 border-b border-base-300 shrink-0">
	<div class="flex items-center gap-2 h-8">
		<a href="/settings" class="btn btn-ghost btn-sm btn-square md:hidden">
			<ChevronLeft size={18} />
		</a>
		<h2 class="font-semibold">Data</h2>
	</div>
</div>

<!-- Scrollable content -->
<div class="flex-1 overflow-y-auto p-4 md:p-6">
<div class="max-w-3xl flex flex-col gap-4">
	<div>
		<p class="text-sm font-medium mb-1">Export workspace</p>
		<p class="text-xs text-base-content/60 mb-2">Download all notes, tasks, projects, and settings as a ZIP file</p>
		<Button variant="ghost" size="sm" loading={exporting} onclick={handleExportWorkspace}>
			<Download size={14} />
			Export Workspace
		</Button>
	</div>
	<div class="border-t border-base-300 pt-4 mt-4">
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
</div>
