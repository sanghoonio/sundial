---
date: 2026-02-14
status: complete
description: Add WebSocket connection status indicator to sidebar with reconnect button
---

# WebSocket Connection Status Indicator

## Context

The WebSocket connection between the UI and API sometimes drops silently. When this happens, notes/tasks created via MCP or the API don't show up in the UI until the user manually reloads the page. There's no visual feedback about connection state, so the user has no way to know the live updates have stopped working.

This adds a small connection indicator to the sidebar that shows current status and doubles as a reconnect button when disconnected.

## Problem in Current Code

The WebSocket store's `connected` flag is inaccurate:
- It's only set `true` when a **message arrives** (not on socket open)
- It's only set `false` when `stop()` is explicitly called (not on socket close)
- So if the server drops, the store still thinks it's connected

## Changes

### 1. WebSocket Service (`ui/src/lib/services/websocket.ts`)

Add connection state callbacks and a manual reconnect method:

- Add `StateHandler` type and `stateHandlers` set (same pattern as existing `MessageHandler`)
- Fire `'connected'` in `ws.onopen`
- Fire `'reconnecting'` in `ws.onclose` (when auto-reconnect is active) and in the `connect()` catch block
- Fire `'disconnected'` in `ws.onclose` when `shouldReconnect` is false
- Add `onStateChange(handler)` method — returns unsubscribe function
- Add `reconnect()` method — closes existing socket, resets backoff, reconnects immediately

### 2. WebSocket Store (`ui/src/lib/stores/websocket.svelte.ts`)

Wire up accurate state tracking:

- Replace `let connected = $state(false)` with `let connectionState = $state<'connected' | 'reconnecting' | 'disconnected'>('disconnected')`
- Register `client.onStateChange()` to update `connectionState`
- Remove the `connected = true` line from the `onMessage` handler
- Keep `get connected()` returning `connectionState === 'connected'` for backward compat
- Add `get connectionState()` for the three-state model
- Add `reconnect()` method delegating to `client.reconnect()`

### 3. Sidebar (`ui/src/lib/components/layout/Sidebar.svelte`)

Add indicator between the external links section and the user profile section:

- Import `Wifi`, `WifiOff` from lucide-svelte and `ws` from the store
- **Connected**: `Wifi` icon (14px) + "Connected" text, `text-success/70` (subtle/faded)
- **Reconnecting**: `WifiOff` icon + "Reconnecting..." text, `text-warning animate-pulse`, clickable to force immediate retry
- **Disconnected**: `WifiOff` icon + "Disconnected" text, `text-error`, clickable to reconnect
- Collapsed mode: icon only (no text), same pattern as all other sidebar items
- Smaller than nav items (14px icon, `text-xs`) — secondary/glanceable info

## Files to Modify

1. `ui/src/lib/services/websocket.ts` — add `onStateChange`, `reconnect`
2. `ui/src/lib/stores/websocket.svelte.ts` — wire state tracking, expose `connectionState` + `reconnect()`
3. `ui/src/lib/components/layout/Sidebar.svelte` — render indicator

## Verification

1. Start the app, check sidebar shows green "Connected" indicator
2. Stop the API server — indicator should turn amber "Reconnecting..." with pulse animation
3. Click the reconnecting indicator — should force an immediate reconnect attempt
4. Restart the API server — indicator should turn green again automatically
5. Collapse the sidebar — indicator should show just the icon, no text
6. Hover the icon in collapsed mode — tooltip should show the state
