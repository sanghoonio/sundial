<script lang="ts">
	import { auth } from '$lib/stores/auth.svelte';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { LogOut } from 'lucide-svelte';

	interface Props {
		title?: string;
	}

	let { title = '' }: Props = $props();

	function handleLogout() {
		auth.logout();
		goto(`${base}/login`);
	}
</script>

<header class="navbar bg-base-100 border-b border-base-300 px-4 h-16 min-h-16">
	<div class="flex-1">
		<h1 class="text-xl font-semibold">{title}</h1>
	</div>
	<div class="flex-none">
		<div class="dropdown dropdown-end">
			<div tabindex="0" role="button" class="btn btn-ghost btn-sm gap-2">
				<span class="hidden sm:inline">{auth.user?.username ?? ''}</span>
				<div class="avatar placeholder">
					<div class="bg-neutral text-neutral-content rounded-full w-8 flex items-center justify-center">
						<span class="text-xs">{(auth.user?.username ?? 'U')[0].toUpperCase()}</span>
					</div>
				</div>
			</div>
			<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
			<ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box shadow-lg z-10 w-40 p-2 border border-base-300">
				<li>
					<button onclick={handleLogout}>
						<LogOut size={16} />
						Log out
					</button>
				</li>
			</ul>
		</div>
	</div>
</header>
