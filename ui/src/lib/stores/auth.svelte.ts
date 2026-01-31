import { api, setToken, clearToken, ApiError } from '$lib/services/api';
import type { TokenResponse, UserResponse } from '$lib/types';

interface AuthState {
	token: string | null;
	user: UserResponse | null;
	loading: boolean;
	ready: boolean;
}

function createAuthStore() {
	let state = $state<AuthState>({
		token: null,
		user: null,
		loading: true,
		ready: false
	});

	return {
		get token() { return state.token; },
		get user() { return state.user; },
		get loading() { return state.loading; },
		get ready() { return state.ready; },
		get isAuthenticated() { return !!state.token && !!state.user; },

		async init() {
			const stored = localStorage.getItem('sundial_token');
			if (!stored) {
				state.loading = false;
				state.ready = true;
				return;
			}
			state.token = stored;
			try {
				state.user = await api.get<UserResponse>('/api/auth/me');
				state.ready = true;
			} catch {
				state.token = null;
				clearToken();
				state.ready = true;
			} finally {
				state.loading = false;
			}
		},

		async login(password: string) {
			const res = await api.post<TokenResponse>('/api/auth/login', { password });
			state.token = res.access_token;
			setToken(res.access_token);
			state.user = await api.get<UserResponse>('/api/auth/me');
		},

		async setup(password: string) {
			const res = await api.post<TokenResponse>('/api/auth/setup', { password });
			state.token = res.access_token;
			setToken(res.access_token);
			state.user = await api.get<UserResponse>('/api/auth/me');
		},

		logout() {
			state.token = null;
			state.user = null;
			clearToken();
		}
	};
}

export const auth = createAuthStore();
