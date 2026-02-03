<script lang="ts">
	import { base } from '$app/paths';
	import { StickyNote, Plus } from 'lucide-svelte';
</script>

<div class="flex flex-col items-center justify-center h-full text-center p-6">
	<StickyNote size={48} class="text-base-content/20 mb-4" />
	<h2 class="text-lg font-medium text-base-content/60 mb-1">Select a note</h2>
	<p class="text-sm text-base-content/40 mb-4">Pick a note from the list or create a new one</p>
	<a href="{base}/notes/new" class="btn btn-primary btn-sm">
		<Plus size={16} />
		New Note
	</a>
</div>
