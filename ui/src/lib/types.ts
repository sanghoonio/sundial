// Auth
export interface TokenResponse {
	access_token: string;
	token_type: string;
}

export interface UserResponse {
	username: string;
	settings: Record<string, unknown>;
}

// Token management
export interface TokenListItem {
	id: string;
	token_type: string;
	name: string | null;
	scope: string;
	last_used_at: string | null;
	created_at: string;
	is_current: boolean;
}

export interface ApiKeyCreatedResponse {
	id: string;
	name: string;
	scope: string;
	raw_token: string;
}

export interface PasswordChangeRequest {
	current_password: string;
	new_password: string;
}

export interface UsernameChangeRequest {
	username: string;
}

export interface CreateApiKeyRequest {
	name: string;
	scope: string;
}

// Notes — Block types
export interface ChatMessage {
	role: 'user' | 'assistant';
	content: string;
}

export interface MarkdownBlockData {
	id: string;
	type: 'md';
	content: string;
	messages?: ChatMessage[];
}

export interface ChatBlockData {
	id: string;
	type: 'chat';
	content?: string;
	messages: ChatMessage[];
}

export type NoteBlock = MarkdownBlockData | ChatBlockData;

// Notes
export interface NoteCreate {
	title: string;
	content?: string;
	tags?: string[];
	project_id?: string | null;
	blocks?: NoteBlock[];
}

export interface NoteUpdate {
	title?: string;
	content?: string;
	tags?: string[];
	project_id?: string | null;
	blocks?: NoteBlock[];
}

export interface NoteResponse {
	id: string;
	title: string;
	filepath: string;
	content: string;
	blocks: NoteBlock[];
	tags: string[];
	project_id: string | null;
	is_archived: boolean;
	linked_notes: string[];
	linked_tasks: string[];
	linked_events: string[];
	created_at: string;
	updated_at: string;
}

export interface NoteListItem {
	id: string;
	title: string;
	filepath: string;
	tags: string[];
	project_id: string | null;
	linked_tasks: string[];
	linked_events: string[];
	preview: string;
	created_at: string;
	updated_at: string;
}

export interface NoteList {
	notes: NoteListItem[];
	total: number;
}

export interface BacklinkItem {
	id: string;
	title: string;
	filepath: string;
}

export interface BacklinkTaskItem {
	id: string;
	title: string;
	status: string;
}

export interface BacklinksResponse {
	notes: BacklinkItem[];
	tasks: BacklinkTaskItem[];
}

// Tasks
export interface ChecklistItemCreate {
	text: string;
	is_checked?: boolean;
}

export interface ChecklistItemResponse {
	id: string;
	text: string;
	is_checked: boolean;
	position: number;
}

export interface TaskCreate {
	title: string;
	description?: string;
	priority?: string;
	due_date?: string | null;
	project_id?: string;
	milestone_id?: string | null;
	source_note_id?: string | null;
	calendar_event_id?: string | null;
	checklist?: ChecklistItemCreate[];
}

export interface TaskUpdate {
	title?: string;
	description?: string;
	status?: string;
	priority?: string;
	due_date?: string | null;
	project_id?: string;
	milestone_id?: string | null;
	checklist?: ChecklistItemCreate[];
}

export interface TaskMove {
	milestone_id: string;
	position?: number;
}

export interface TaskResponse {
	id: string;
	title: string;
	description: string;
	status: string;
	priority: string;
	due_date: string | null;
	project_id: string;
	milestone_id: string | null;
	source_note_id: string | null;
	calendar_event_id: string | null;
	ai_suggested: boolean;
	position: number;
	completed_at: string | null;
	checklist: ChecklistItemResponse[];
	created_at: string;
	updated_at: string;
}

export interface TaskList {
	tasks: TaskResponse[];
	total: number;
}

// Projects
export interface MilestoneCreate {
	name: string;
	position?: number;
}

export interface MilestoneResponse {
	id: string;
	name: string;
	position: number;
}

export interface ProjectCreate {
	id: string;
	name: string;
	description?: string;
	color?: string;
	milestones?: MilestoneCreate[];
}

export interface ProjectUpdate {
	name?: string;
	description?: string;
	color?: string;
	status?: string;
}

export interface ProjectResponse {
	id: string;
	name: string;
	description: string;
	color: string;
	status: string;
	milestones: MilestoneResponse[];
	task_count: number;
	created_at: string;
	updated_at: string;
}

export interface ProjectList {
	projects: ProjectResponse[];
	total: number;
}

// Linked item refs (returned by event endpoints)
export interface LinkedNoteRef {
	id: string;
	title: string;
}

export interface LinkedTaskRef {
	id: string;
	title: string;
	status: string;
}

// Calendar
export interface EventCreate {
	title: string;
	description?: string;
	start_time: string;
	end_time?: string | null;
	all_day?: boolean;
	location?: string;
	rrule?: string | null;
}

export interface EventUpdate {
	title?: string;
	description?: string;
	start_time?: string;
	end_time?: string | null;
	all_day?: boolean;
	location?: string;
	rrule?: string | null;
}

export interface EventResponse {
	id: string;
	title: string;
	description: string;
	start_time: string;
	end_time: string | null;
	all_day: boolean;
	location: string;
	calendar_source: string;
	calendar_id: string;
	rrule: string | null;
	recurring_event_id: string | null;
	recurrence_id: string | null;
	linked_notes: LinkedNoteRef[];
	linked_tasks: LinkedTaskRef[];
	synced_at: string | null;
	created_at: string;
	updated_at: string;
}

export interface EventList {
	events: EventResponse[];
	total: number;
}

// Calendar items (unified type for events + tasks on calendar)
export type CalendarItem =
	| { type: 'event'; data: EventResponse }
	| { type: 'task'; data: TaskResponse };

// Dashboard
export interface DashboardEvent {
	id: string;
	title: string;
	start_time: string;
	end_time: string | null;
	all_day: boolean;
}

export interface DashboardTask {
	id: string;
	title: string;
	status: string;
	priority: string;
	due_date: string | null;
	project_id: string;
}

export interface DashboardNote {
	id: string;
	title: string;
	updated_at: string;
}

export interface DashboardResponse {
	date: string;
	calendar_events: DashboardEvent[];
	tasks_due: DashboardTask[];
	tasks_linked_to_events: DashboardTask[];
	recent_notes: DashboardNote[];
	suggestions: unknown[];
}

// Tags
export interface TagWithCount {
	name: string;
	count: number;
}

export interface TagListResponse {
	tags: TagWithCount[];
}

// Search
export interface SearchResultItem {
	id: string;
	title: string;
	filepath: string;
	snippet: string;
	rank: number;
}

export interface TaskSearchResultItem {
	id: string;
	title: string;
	description: string;
	status: string;
	project_id: string;
}

export interface SearchResult {
	results: SearchResultItem[];
	tasks: TaskSearchResultItem[];
	total: number;
	query: string;
}

// Settings
export interface SettingsResponse {
	ai_enabled: boolean;
	ai_auto_tag: boolean;
	ai_auto_extract_tasks: boolean;
	openrouter_api_key: string;
	openrouter_model: string;
	calendar_source: string;
	calendar_sync_enabled: boolean;
	theme: string;
}

export interface SettingsUpdate {
	ai_enabled?: boolean;
	ai_auto_tag?: boolean;
	ai_auto_extract_tasks?: boolean;
	openrouter_api_key?: string;
	openrouter_model?: string;
	calendar_source?: string;
	calendar_sync_enabled?: boolean;
	theme?: string;
}

// Calendar Settings (CalDAV)
export interface CalendarSettingsResponse {
	calendar_source: string;
	sync_enabled: boolean;
	selected_calendars: string[];
	sync_range_past_days: number;
	sync_range_future_days: number;
	sync_interval_minutes: number;
	sync_direction: string;
	caldav_server_url: string;
	caldav_username: string;
	caldav_has_password: boolean;
	last_sync_at: string | null;
	last_sync_error: string | null;
}

export interface CalendarSettingsUpdate {
	calendar_source?: string;
	sync_enabled?: boolean;
	selected_calendars?: string[];
	sync_range_past_days?: number;
	sync_range_future_days?: number;
	sync_interval_minutes?: number;
	sync_direction?: string;
	caldav_server_url?: string;
	caldav_username?: string;
	caldav_password?: string;
}

export interface CalendarSyncResult {
	synced_events: number;
	created: number;
	updated: number;
	deleted: number;
	errors: string[];
	last_sync: string | null;
}

export interface CalDAVCalendarInfo {
	id: string;
	name: string;
	color: string;
}

// WebSocket
export interface WSMessage {
	type: string;
	data: Record<string, unknown>;
}
