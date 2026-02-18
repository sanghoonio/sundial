import { base } from '$app/paths';
import { clientId } from '$lib/clientId';
import type { TaskList, TaskResponse } from '$lib/types';

const TOKEN_KEY = 'sundial_token';

export class ApiError extends Error {
	constructor(
		public status: number,
		public detail: string
	) {
		super(detail);
	}
}

function getToken(): string | null {
	return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
	localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
	localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
	const headers: Record<string, string> = {
		'X-Client-ID': clientId
	};
	const token = getToken();
	if (token) {
		headers['Authorization'] = `Bearer ${token}`;
	}
	if (body !== undefined) {
		headers['Content-Type'] = 'application/json';
	}

	const fullPath = `${base}${path}`;
	const res = await fetch(fullPath, {
		method,
		headers,
		body: body !== undefined ? JSON.stringify(body) : undefined
	});

	if (!res.ok) {
		let detail = res.statusText;
		try {
			const err = await res.json();
			detail = err.detail || detail;
		} catch {
			// ignore parse errors
		}
		throw new ApiError(res.status, detail);
	}

	if (res.status === 204) {
		return undefined as T;
	}

	return res.json();
}

const PAGE_SIZE = 200;

/**
 * Fetch tasks matching a query, paginating through the API automatically.
 * The backend returns incomplete tasks first, so when `includeCompleted`
 * is false (default) we can stop after the first page — no need to fetch
 * done tasks that won't be displayed.
 */
export async function fetchAllTasks(query = '', includeCompleted = false): Promise<TaskList> {
	const sep = query ? `${query}&` : '';
	const tasks: TaskResponse[] = [];
	let offset = 0;
	let total = 0;
	do {
		const res = await request<TaskList>(
			'GET',
			`/api/tasks?${sep}limit=${PAGE_SIZE}&offset=${offset}`
		);
		tasks.push(...res.tasks);
		total = res.total;
		offset += PAGE_SIZE;
		// Backend sorts incomplete first. If we don't need completed tasks,
		// stop as soon as we see one (everything after is also done).
		if (!includeCompleted && res.tasks.some((t) => t.status === 'done')) {
			return { tasks: tasks.filter((t) => t.status !== 'done'), total };
		}
	} while (tasks.length < total);
	return { tasks, total };
}

export const api = {
	get: <T>(path: string) => request<T>('GET', path),
	post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
	put: <T>(path: string, body?: unknown) => request<T>('PUT', path, body),
	delete: <T>(path: string) => request<T>('DELETE', path),
	authHeaders(): Record<string, string> {
		const token = getToken();
		return token ? { Authorization: `Bearer ${token}` } : {};
	}
};
