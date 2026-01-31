# Frontend Specification

## Architecture

### Svelte Application Structure
```
ui/
├── src/
│   ├── app.html              # HTML template
│   ├── routes/
│   │   ├── +layout.svelte    # Root layout with nav
│   │   ├── +page.svelte      # Dashboard/home
│   │   ├── notes/
│   │   │   ├── +page.svelte          # Notes list
│   │   │   ├── [id]/+page.svelte     # Single note view/edit
│   │   │   └── new/+page.svelte      # Create note
│   │   ├── tasks/
│   │   │   └── +page.svelte          # Kanban board
│   │   ├── projects/
│   │   │   ├── +page.svelte          # Project list
│   │   │   └── [id]/+page.svelte     # Project kanban
│   │   ├── calendar/
│   │   │   └── +page.svelte          # Calendar view
│   │   ├── search/
│   │   │   └── +page.svelte          # Search results
│   │   └── settings/
│   │       └── +page.svelte          # Settings
│   ├── lib/
│   │   ├── components/
│   │   │   ├── ui/                   # Base components
│   │   │   │   ├── Button.svelte
│   │   │   │   ├── Input.svelte
│   │   │   │   ├── Card.svelte
│   │   │   │   ├── Modal.svelte
│   │   │   │   ├── Dropdown.svelte
│   │   │   │   ├── Toast.svelte
│   │   │   │   └── Badge.svelte
│   │   │   ├── layout/               # Layout components
│   │   │   │   ├── Sidebar.svelte
│   │   │   │   ├── Header.svelte
│   │   │   │   └── Container.svelte
│   │   │   ├── notes/
│   │   │   │   ├── NoteEditor.svelte        # Block-based editor
│   │   │   │   ├── MarkdownBlock.svelte     # Text block
│   │   │   │   ├── ChatBlock.svelte         # AI chat block
│   │   │   │   ├── NoteCard.svelte          # List view card
│   │   │   │   └── TagInput.svelte
│   │   │   ├── tasks/
│   │   │   │   ├── KanbanBoard.svelte
│   │   │   │   ├── KanbanColumn.svelte
│   │   │   │   ├── TaskCard.svelte
│   │   │   │   └── TaskQuickAdd.svelte
│   │   │   ├── calendar/
│   │   │   │   ├── CalendarGrid.svelte
│   │   │   │   └── EventCard.svelte
│   │   │   └── shared/
│   │   │       ├── LinkPreview.svelte       # [[link]] preview
│   │   │       ├── SearchBar.svelte
│   │   │       └── DatePicker.svelte
│   │   ├── stores/
│   │   │   ├── auth.js               # Auth state
│   │   │   ├── notes.js              # Notes store
│   │   │   ├── tasks.js              # Tasks store
│   │   │   ├── calendar.js           # Calendar events
│   │   │   ├── settings.js           # User settings
│   │   │   └── websocket.js          # WS connection
│   │   ├── services/
│   │   │   ├── api.js                # API client wrapper
│   │   │   ├── auth.js               # Auth service
│   │   │   └── websocket.js          # WebSocket client
│   │   └── utils/
│   │       ├── markdown.js           # Markdown parsing helpers
│   │       ├── linkParser.js         # Parse [[links]]
│   │       ├── dateFormatter.js
│   │       └── slugify.js
│   └── app.css                       # Global styles + Tailwind
├── static/
│   └── favicon.png
├── tailwind.config.js
├── vite.config.js
└── package.json
```

## Component Library (shadcn-inspired)

### Design Philosophy
- Built with Tailwind + DaisyUI classes
- Composable and accessible
- Unstyled primitive approach (no imposed design)
- Props for variants and states
- Lucide icons only

### Base Components (`lib/components/ui/`)

#### Button.svelte
```svelte
<script>
  export let variant = 'primary';  // primary, secondary, ghost, danger
  export let size = 'md';           // sm, md, lg
  export let disabled = false;
  export let type = 'button';
  export let loading = false;
</script>

<button
  {type}
  {disabled}
  class="btn {variant} {size} {$$props.class || ''}"
  on:click
>
  {#if loading}
    <span class="loading loading-spinner"></span>
  {/if}
  <slot />
</button>
```

#### Input.svelte
```svelte
<script>
  export let value = '';
  export let placeholder = '';
  export let type = 'text';
  export let error = '';
</script>

<div class="form-control">
  <input
    {type}
    {placeholder}
    bind:value
    class="input input-bordered {error ? 'input-error' : ''}"
    on:input
    on:blur
  />
  {#if error}
    <label class="label">
      <span class="label-text-alt text-error">{error}</span>
    </label>
  {/if}
</div>
```

#### Card.svelte
```svelte
<script>
  export let hoverable = false;
  export let padding = 'md';  // sm, md, lg, none
</script>

<div class="card bg-base-100 shadow-md {hoverable ? 'hover:shadow-lg transition-shadow' : ''} {$$props.class || ''}">
  <div class="card-body {padding === 'none' ? 'p-0' : padding === 'sm' ? 'p-2' : padding === 'lg' ? 'p-8' : 'p-4'}">
    <slot />
  </div>
</div>
```

#### Modal.svelte
```svelte
<script>
  export let open = false;
  export let title = '';
  export let onClose = () => {};
</script>

<dialog class="modal" class:modal-open={open}>
  <div class="modal-box">
    <h3 class="font-bold text-lg">{title}</h3>
    <button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2" on:click={onClose}>✕</button>
    
    <div class="py-4">
      <slot />
    </div>
    
    <div class="modal-action">
      <slot name="actions">
        <button class="btn" on:click={onClose}>Close</button>
      </slot>
    </div>
  </div>
  <form method="dialog" class="modal-backdrop" on:click={onClose}>
    <button>close</button>
  </form>
</dialog>
```

#### Toast.svelte
```svelte
<script>
  import { toasts } from '$lib/stores/toasts';
  import { fade } from 'svelte/transition';
</script>

<div class="toast toast-end">
  {#each $toasts as toast (toast.id)}
    <div class="alert alert-{toast.type}" transition:fade>
      <span>{toast.message}</span>
      <button class="btn btn-sm btn-ghost" on:click={() => toasts.remove(toast.id)}>✕</button>
    </div>
  {/each}
</div>
```

#### Badge.svelte
```svelte
<script>
  export let variant = 'default';  // default, success, warning, error
  export let size = 'md';           // sm, md, lg
  export let removable = false;
  export let onRemove = () => {};
</script>

<div class="badge badge-{variant} {size === 'sm' ? 'badge-sm' : size === 'lg' ? 'badge-lg' : ''} {$$props.class || ''}">
  <slot />
  {#if removable}
    <button class="ml-1" on:click={onRemove}>×</button>
  {/if}
</div>
```

## Feature Components

### Note Editor (`lib/components/notes/NoteEditor.svelte`)

**Block-based interface like Jupyter/Observable**

```svelte
<script>
  import { createEventDispatcher } from 'svelte';
  import MarkdownBlock from './MarkdownBlock.svelte';
  import ChatBlock from './ChatBlock.svelte';
  import { Plus } from 'lucide-svelte';
  
  export let noteId = null;
  export let blocks = [];  // [{type: 'markdown', content: '...'}, {type: 'chat', messages: [...]}]
  
  const dispatch = createEventDispatcher();
  
  function addBlock(type) {
    blocks = [...blocks, { type, content: '', id: crypto.randomUUID() }];
  }
  
  function removeBlock(blockId) {
    blocks = blocks.filter(b => b.id !== blockId);
  }
  
  function moveBlock(blockId, direction) {
    const index = blocks.findIndex(b => b.id === blockId);
    if (direction === 'up' && index > 0) {
      [blocks[index], blocks[index - 1]] = [blocks[index - 1], blocks[index]];
    } else if (direction === 'down' && index < blocks.length - 1) {
      [blocks[index], blocks[index + 1]] = [blocks[index + 1], blocks[index]];
    }
    blocks = [...blocks];
  }
</script>

<div class="note-editor space-y-4">
  {#each blocks as block, index (block.id)}
    <div class="block-container">
      {#if block.type === 'markdown'}
        <MarkdownBlock
          bind:content={block.content}
          on:remove={() => removeBlock(block.id)}
          on:moveUp={() => moveBlock(block.id, 'up')}
          on:moveDown={() => moveBlock(block.id, 'down')}
        />
      {:else if block.type === 'chat'}
        <ChatBlock
          {noteId}
          bind:messages={block.messages}
          on:remove={() => removeBlock(block.id)}
          on:moveUp={() => moveBlock(block.id, 'up')}
          on:moveDown={() => moveBlock(block.id, 'down')}
        />
      {/if}
    </div>
  {/each}
  
  <div class="flex gap-2 justify-center pt-4">
    <button class="btn btn-sm btn-ghost" on:click={() => addBlock('markdown')}>
      <Plus size={16} /> Text
    </button>
    <button class="btn btn-sm btn-ghost" on:click={() => addBlock('chat')}>
      <Plus size={16} /> Chat
    </button>
  </div>
</div>
```

### Markdown Block (`lib/components/notes/MarkdownBlock.svelte`)

**WYSIWYG editor with toolbar**

```svelte
<script>
  import { createEventDispatcher } from 'svelte';
  import { Bold, Italic, Code, List, ChevronUp, ChevronDown, X } from 'lucide-svelte';
  
  export let content = '';
  
  const dispatch = createEventDispatcher();
  let editorRef;
  let showToolbar = false;
  
  // Simple WYSIWYG helpers
  function formatText(format) {
    // Implementation: insert markdown syntax at cursor
  }
</script>

<div class="markdown-block border rounded-lg p-4 hover:border-primary transition-colors"
     on:mouseenter={() => showToolbar = true}
     on:mouseleave={() => showToolbar = false}>
  
  {#if showToolbar}
    <div class="toolbar flex gap-1 mb-2 border-b pb-2">
      <button class="btn btn-xs btn-ghost" on:click={() => formatText('bold')}><Bold size={14} /></button>
      <button class="btn btn-xs btn-ghost" on:click={() => formatText('italic')}><Italic size={14} /></button>
      <button class="btn btn-xs btn-ghost" on:click={() => formatText('code')}><Code size={14} /></button>
      <button class="btn btn-xs btn-ghost" on:click={() => formatText('list')}><List size={14} /></button>
      <div class="flex-1"></div>
      <button class="btn btn-xs btn-ghost" on:click={() => dispatch('moveUp')}><ChevronUp size={14} /></button>
      <button class="btn btn-xs btn-ghost" on:click={() => dispatch('moveDown')}><ChevronDown size={14} /></button>
      <button class="btn btn-xs btn-ghost text-error" on:click={() => dispatch('remove')}><X size={14} /></button>
    </div>
  {/if}
  
  <div contenteditable="true"
       bind:innerHTML={content}
       bind:this={editorRef}
       class="prose max-w-none focus:outline-none min-h-[100px]"
       on:input={(e) => content = e.target.innerHTML}>
  </div>
</div>
```

### Chat Block (`lib/components/notes/ChatBlock.svelte`)

**AI chat interface within note**

```svelte
<script>
  import { createEventDispatcher } from 'svelte';
  import { Send, ChevronUp, ChevronDown, X, Minimize2 } from 'lucide-svelte';
  import { api } from '$lib/services/api';
  
  export let noteId;
  export let messages = [];  // [{role: 'user', content: '...'}, {role: 'assistant', content: '...'}]
  
  const dispatch = createEventDispatcher();
  let inputMessage = '';
  let loading = false;
  let collapsed = false;
  
  async function sendMessage() {
    if (!inputMessage.trim()) return;
    
    messages = [...messages, { role: 'user', content: inputMessage }];
    const userMessage = inputMessage;
    inputMessage = '';
    loading = true;
    
    try {
      const response = await api.post('/api/ai/chat', {
        note_id: noteId,
        message: userMessage
      });
      
      messages = [...messages, { role: 'assistant', content: response.response }];
    } catch (error) {
      console.error('Chat error:', error);
    } finally {
      loading = false;
    }
  }
</script>

<div class="chat-block border-2 border-dashed border-primary/50 rounded-lg p-4">
  <div class="flex items-center justify-between mb-2">
    <div class="flex items-center gap-2">
      <div class="badge badge-primary badge-sm">AI Chat</div>
      {#if messages.length > 0}
        <span class="text-xs text-gray-500">{messages.length} messages</span>
      {/if}
    </div>
    
    <div class="flex gap-1">
      <button class="btn btn-xs btn-ghost" on:click={() => collapsed = !collapsed}>
        <Minimize2 size={14} />
      </button>
      <button class="btn btn-xs btn-ghost" on:click={() => dispatch('moveUp')}><ChevronUp size={14} /></button>
      <button class="btn btn-xs btn-ghost" on:click={() => dispatch('moveDown')}><ChevronDown size={14} /></button>
      <button class="btn btn-xs btn-ghost text-error" on:click={() => dispatch('remove')}><X size={14} /></button>
    </div>
  </div>
  
  {#if !collapsed}
    <div class="messages space-y-2 max-h-96 overflow-y-auto mb-4">
      {#each messages as message}
        <div class="chat {message.role === 'user' ? 'chat-end' : 'chat-start'}">
          <div class="chat-bubble {message.role === 'user' ? 'chat-bubble-primary' : ''}">
            {message.content}
          </div>
        </div>
      {/each}
      
      {#if loading}
        <div class="chat chat-start">
          <div class="chat-bubble">
            <span class="loading loading-dots loading-sm"></span>
          </div>
        </div>
      {/if}
    </div>
    
    <div class="flex gap-2">
      <input
        type="text"
        placeholder="Ask something..."
        class="input input-bordered flex-1"
        bind:value={inputMessage}
        on:keydown={(e) => e.key === 'Enter' && sendMessage()}
      />
      <button class="btn btn-primary" on:click={sendMessage} disabled={loading}>
        <Send size={16} />
      </button>
    </div>
  {/if}
</div>
```

### Kanban Board (`lib/components/tasks/KanbanBoard.svelte`)

**Drag-and-drop task management**

```svelte
<script>
  import { writable } from 'svelte/store';
  import KanbanColumn from './KanbanColumn.svelte';
  import TaskCard from './TaskCard.svelte';
  import { api } from '$lib/services/api';
  
  export let projectId;
  export let columns = [];  // [{id, title, tasks: []}]
  
  let draggedTask = null;
  
  function handleDragStart(task) {
    draggedTask = task;
  }
  
  async function handleDrop(columnId) {
    if (!draggedTask) return;
    
    await api.put(`/api/tasks/${draggedTask.id}/move`, {
      milestone_id: columnId
    });
    
    // Update local state
    columns = columns.map(col => ({
      ...col,
      tasks: col.id === columnId 
        ? [...col.tasks.filter(t => t.id !== draggedTask.id), draggedTask]
        : col.tasks.filter(t => t.id !== draggedTask.id)
    }));
    
    draggedTask = null;
  }
</script>

<div class="kanban-board flex gap-4 overflow-x-auto pb-4">
  {#each columns as column (column.id)}
    <KanbanColumn
      {column}
      on:drop={() => handleDrop(column.id)}
      on:dragstart={(e) => handleDragStart(e.detail)}
    />
  {/each}
</div>
```

### Task Card (`lib/components/tasks/TaskCard.svelte`)

**Individual task with suggestion state**

```svelte
<script>
  import { createEventDispatcher } from 'svelte';
  import { Calendar, FileText, Check, X } from 'lucide-svelte';
  
  export let task;
  
  const dispatch = createEventDispatcher();
  
  async function acceptSuggestion() {
    await api.post(`/api/tasks/${task.id}/accept`);
    task.ai_suggested = false;
    dispatch('accepted');
  }
  
  async function dismissSuggestion() {
    await api.delete(`/api/tasks/${task.id}`);
    dispatch('dismissed');
  }
</script>

<div
  class="task-card card bg-base-100 shadow-sm hover:shadow-md transition-shadow cursor-move mb-2"
  class:opacity-60={task.ai_suggested}
  class:border-2={task.ai_suggested}
  class:border-dashed={task.ai_suggested}
  class:border-primary={task.ai_suggested}
  draggable="true"
  on:dragstart
>
  <div class="card-body p-3">
    {#if task.ai_suggested}
      <div class="flex gap-1 mb-2">
        <button class="btn btn-xs btn-success" on:click={acceptSuggestion}>
          <Check size={12} /> Accept
        </button>
        <button class="btn btn-xs btn-ghost" on:click={dismissSuggestion}>
          <X size={12} /> Dismiss
        </button>
      </div>
    {/if}
    
    <h4 class="text-sm font-medium">{task.title}</h4>
    
    {#if task.description}
      <p class="text-xs text-gray-600 mt-1">{task.description}</p>
    {/if}
    
    <div class="flex gap-2 mt-2 text-xs text-gray-500">
      {#if task.due_date}
        <div class="flex items-center gap-1">
          <Calendar size={12} />
          {new Date(task.due_date).toLocaleDateString()}
        </div>
      {/if}
      
      {#if task.source_note_id}
        <div class="flex items-center gap-1">
          <FileText size={12} />
          From note
        </div>
      {/if}
    </div>
    
    {#if task.checklist?.length > 0}
      <div class="mt-2 space-y-1">
        {#each task.checklist as item}
          <label class="flex items-center gap-2 text-xs">
            <input type="checkbox" class="checkbox checkbox-xs" checked={item.completed} />
            {item.text}
          </label>
        {/each}
      </div>
    {/if}
  </div>
</div>
```

## Stores (State Management)

### Auth Store (`lib/stores/auth.js`)
```javascript
import { writable } from 'svelte/store';
import { browser } from '$app/environment';

function createAuthStore() {
  const { subscribe, set } = writable({
    token: browser ? localStorage.getItem('token') : null,
    user: null,
    loading: false
  });

  return {
    subscribe,
    login: async (username, password) => {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      
      const data = await response.json();
      if (browser) localStorage.setItem('token', data.access_token);
      set({ token: data.access_token, user: data.user, loading: false });
    },
    logout: () => {
      if (browser) localStorage.removeItem('token');
      set({ token: null, user: null, loading: false });
    }
  };
}

export const auth = createAuthStore();
```

### WebSocket Store (`lib/stores/websocket.js`)
```javascript
import { writable } from 'svelte/store';
import { toasts } from './toasts';

function createWebSocketStore() {
  const { subscribe, set } = writable({ connected: false });
  let ws = null;

  return {
    subscribe,
    connect: () => {
      ws = new WebSocket('ws://localhost:8000/ws');
      
      ws.onopen = () => set({ connected: true });
      ws.onclose = () => set({ connected: false });
      
      ws.onmessage = (event) => {
        const update = JSON.parse(event.data);
        
        // Handle different update types
        if (update.type === 'tags_added') {
          // Dispatch to notes store
        } else if (update.type === 'tasks_extracted') {
          toasts.add(`${update.tasks.length} tasks added`, 'success');
        }
      };
    },
    disconnect: () => {
      if (ws) ws.close();
    }
  };
}

export const websocket = createWebSocketStore();
```

## Routing & Pages

### Dashboard (`routes/+page.svelte`)
```svelte
<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/services/api';
  import EventCard from '$lib/components/calendar/EventCard.svelte';
  import TaskCard from '$lib/components/tasks/TaskCard.svelte';
  import NoteCard from '$lib/components/notes/NoteCard.svelte';
  
  let dashboard = null;
  
  onMount(async () => {
    dashboard = await api.get('/api/dashboard/today');
  });
</script>

<div class="container mx-auto p-6">
  <h1 class="text-3xl font-bold mb-6">Today</h1>
  
  {#if dashboard}
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- Calendar Events -->
      <div class="card bg-base-100 shadow-md">
        <div class="card-body">
          <h2 class="card-title">Calendar</h2>
          {#each dashboard.calendar_events as event}
            <EventCard {event} />
          {/each}
        </div>
      </div>
      
      <!-- Tasks Due -->
      <div class="card bg-base-100 shadow-md">
        <div class="card-body">
          <h2 class="card-title">Tasks</h2>
          {#each dashboard.tasks_due as task}
            <TaskCard {task} />
          {/each}
        </div>
      </div>
      
      <!-- Recent Notes -->
      <div class="card bg-base-100 shadow-md col-span-2">
        <div class="card-body">
          <h2 class="card-title">Recent Notes</h2>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            {#each dashboard.recent_notes as note}
              <NoteCard {note} />
            {/each}
          </div>
        </div>
      </div>
    </div>
  {/if}
</div>
```

### Notes List (`routes/notes/+page.svelte`)
```svelte
<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/services/api';
  import SearchBar from '$lib/components/shared/SearchBar.svelte';
  import NoteCard from '$lib/components/notes/NoteCard.svelte';
  import { Plus } from 'lucide-svelte';
  
  let notes = [];
  let searchQuery = '';
  let selectedTags = [];
  
  async function loadNotes() {
    const params = new URLSearchParams();
    if (searchQuery) params.append('search', searchQuery);
    if (selectedTags.length) params.append('tags', selectedTags.join(','));
    
    const response = await api.get(`/api/notes?${params}`);
    notes = response.notes;
  }
  
  onMount(loadNotes);
</script>

<div class="container mx-auto p-6">
  <div class="flex justify-between items-center mb-6">
    <h1 class="text-3xl font-bold">Notes</h1>
    <a href="/notes/new" class="btn btn-primary">
      <Plus size={20} /> New Note
    </a>
  </div>
  
  <SearchBar bind:value={searchQuery} on:search={loadNotes} />
  
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
    {#each notes as note}
      <NoteCard {note} />
    {/each}
  </div>
</div>
```

### Single Note (`routes/notes/[id]/+page.svelte`)
```svelte
<script>
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { api } from '$lib/services/api';
  import NoteEditor from '$lib/components/notes/NoteEditor.svelte';
  import TagInput from '$lib/components/notes/TagInput.svelte';
  import Button from '$lib/components/ui/Button.svelte';
  import { Save } from 'lucide-svelte';
  
  let note = null;
  let saving = false;
  
  onMount(async () => {
    const noteId = $page.params.id;
    note = await api.get(`/api/notes/${noteId}`);
  });
  
  async function saveNote() {
    saving = true;
    await api.put(`/api/notes/${note.id}`, {
      title: note.title,
      content: note.content,
      tags: note.tags
    });
    saving = false;
  }
</script>

{#if note}
  <div class="container mx-auto p-6 max-w-4xl">
    <input
      type="text"
      bind:value={note.title}
      class="input input-ghost text-3xl font-bold w-full mb-4"
      placeholder="Note title"
    />
    
    <TagInput bind:tags={note.tags} />
    
    <NoteEditor bind:blocks={note.blocks} noteId={note.id} />
    
    <div class="fixed bottom-6 right-6">
      <Button variant="primary" size="lg" on:click={saveNote} loading={saving}>
        <Save size={20} /> Save
      </Button>
    </div>
  </div>
{/if}
```

## Styling

### Tailwind Configuration (`tailwind.config.js`)
```javascript
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      typography: {
        DEFAULT: {
          css: {
            maxWidth: 'none',
            color: 'inherit',
            a: { color: 'inherit', textDecoration: 'underline' },
            code: { color: 'inherit' }
          }
        }
      }
    }
  },
  plugins: [
    require('daisyui'),
    require('@tailwindcss/typography')
  ],
  daisyui: {
    themes: ['light', 'dark'],
    darkTheme: 'dark',
    base: true,
    styled: true,
    utils: true
  }
};
```

### Global Styles (`app.css`)
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Custom focus styles */
@layer base {
  :focus-visible {
    @apply outline-2 outline-offset-2 outline-primary;
  }
}

/* Smooth transitions */
@layer utilities {
  .transition-base {
    @apply transition-all duration-200 ease-in-out;
  }
}

/* Link styles within markdown */
.prose a[href^="[["] {
  @apply text-primary no-underline hover:underline;
}

/* Suggested items styling */
.ai-suggested {
  @apply opacity-60 border-2 border-dashed border-primary/50;
}
```

## Mobile Considerations

### Responsive Breakpoints
- Mobile: `< 768px` - Single column, bottom navigation
- Tablet: `768px - 1024px` - Two columns, sidebar collapses
- Desktop: `> 1024px` - Full layout

### Mobile-Specific Features
```svelte
<!-- Mobile Navigation (Bottom) -->
<nav class="btm-nav md:hidden">
  <button>
    <Home size={20} />
  </button>
  <button>
    <FileText size={20} />
  </button>
  <button>
    <CheckSquare size={20} />
  </button>
  <button>
    <Calendar size={20} />
  </button>
</nav>

<!-- Touch-friendly sizes -->
<button class="btn btn-lg">  <!-- Larger tap targets on mobile -->
```

### Mobile Gestures
- Swipe between kanban columns
- Pull-to-refresh on lists
- Long-press for context menus
- Tap outside to close modals

## Performance Optimizations

### Lazy Loading
```svelte
<script>
  import { onMount } from 'svelte';
  
  let NoteEditor;
  
  onMount(async () => {
    const module = await import('$lib/components/notes/NoteEditor.svelte');
    NoteEditor = module.default;
  });
</script>
```

### Virtual Scrolling
For long lists (notes, tasks), implement virtual scrolling:
```svelte
<script>
  import { VirtualList } from 'svelte-virtual-list';
</script>

<VirtualList items={notes} let:item>
  <NoteCard note={item} />
</VirtualList>
```

### Debounced Search
```javascript
import { debounce } from '$lib/utils/debounce';

const debouncedSearch = debounce(async (query) => {
  const results = await api.get(`/api/search?q=${query}`);
  // Update results
}, 300);
```

## Testing Approach

### Component Tests (Vitest + Testing Library)
```javascript
import { render, fireEvent } from '@testing-library/svelte';
import Button from '$lib/components/ui/Button.svelte';

test('button renders with text', () => {
  const { getByText } = render(Button, { props: { children: 'Click me' } });
  expect(getByText('Click me')).toBeInTheDocument();
});
```

### E2E Tests (Playwright)
```javascript
test('create note flow', async ({ page }) => {
  await page.goto('/notes/new');
  await page.fill('input[placeholder="Note title"]', 'Test Note');
  await page.fill('textarea', 'Test content');
  await page.click('button:has-text("Save")');
  
  await expect(page).toHaveURL(/\/notes\/note_/);
});
```

## Build & Deployment

### Development
```bash
npm run dev
# Runs on http://localhost:5173
```

### Production Build
```bash
npm run build
npm run preview
```

### Static File Serving
Build outputs to `build/` directory, serve with nginx:
```nginx
server {
    listen 80;
    root /var/www/workspace/ui/build;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
    }
}
```

## Accessibility

- Semantic HTML throughout
- ARIA labels on interactive elements
- Keyboard navigation support (Tab, Enter, Escape)
- Focus management in modals
- Screen reader announcements for dynamic updates
- Color contrast ratios meet WCAG AA standards
- Reduced motion support via `prefers-reduced-motion`
