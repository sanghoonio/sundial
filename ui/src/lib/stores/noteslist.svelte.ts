let _refreshCounter = $state(0);

export const notesList = {
	get refreshKey() {
		return _refreshCounter;
	},
	refresh() {
		_refreshCounter++;
	}
};
