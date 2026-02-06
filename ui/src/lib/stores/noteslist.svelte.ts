import type { NoteListItem } from '$lib/types';

let _refreshCounter = $state(0);
let _patchedNote = $state<NoteListItem | null>(null);

export const notesList = {
	get refreshKey() {
		return _refreshCounter;
	},
	refresh() {
		_refreshCounter++;
	},
	get patchedNote() {
		return _patchedNote;
	},
	patchNote(data: NoteListItem) {
		_patchedNote = data;
	}
};
