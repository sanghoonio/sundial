type ConfirmOptions = {
	title?: string;
	message: string;
	confirmText?: string;
	cancelText?: string;
	variant?: 'default' | 'danger' | 'warning';
};

let _isOpen = $state(false);
let _title = $state('Confirm');
let _message = $state('');
let _confirmText = $state('Confirm');
let _cancelText = $state('Cancel');
let _variant = $state<'default' | 'danger' | 'warning'>('default');
let _resolver: ((value: boolean) => void) | null = null;

export const confirmModal = {
	get isOpen() {
		return _isOpen;
	},
	get title() {
		return _title;
	},
	get message() {
		return _message;
	},
	get confirmText() {
		return _confirmText;
	},
	get cancelText() {
		return _cancelText;
	},
	get variant() {
		return _variant;
	},

	confirm(options: ConfirmOptions): Promise<boolean> {
		_title = options.title ?? 'Confirm';
		_message = options.message;
		_confirmText = options.confirmText ?? 'Confirm';
		_cancelText = options.cancelText ?? 'Cancel';
		_variant = options.variant ?? 'default';
		_isOpen = true;

		return new Promise((resolve) => {
			_resolver = resolve;
		});
	},

	resolve(value: boolean) {
		_isOpen = false;
		if (_resolver) {
			_resolver(value);
			_resolver = null;
		}
	}
};
