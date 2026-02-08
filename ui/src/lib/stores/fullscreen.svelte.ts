let _active = $state(false);

export const fullscreen = {
	get active() {
		return _active;
	},
	toggle() {
		_active = !_active;
	},
	exit() {
		_active = false;
	}
};
