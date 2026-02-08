let _requestKey = $state(0);
let _findQuery = $state('');
let _currentMatch = $state<{ blockIndex: number; start: number; end: number } | null>(null);

export const notesSearch = {
	get requestKey() {
		return _requestKey;
	},
	requestFocus() {
		_requestKey++;
	},
	get findQuery() {
		return _findQuery;
	},
	set findQuery(q: string) {
		_findQuery = q;
	},
	get currentMatch() {
		return _currentMatch;
	},
	set currentMatch(m: { blockIndex: number; start: number; end: number } | null) {
		_currentMatch = m;
	}
};
