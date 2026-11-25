<script lang="ts">
	import MoonIcon from '@lucide/svelte/icons/moon';
	import SunIcon from '@lucide/svelte/icons/sun';
	import { Button } from '#lib/components/ui/button/index.js';
	import { session } from '#lib/stores/session.svelte.js';
</script>

<Button
	variant="ghost"
	size="icon-sm"
	title={session.theme === 'dark' ? 'Açık temaya geç' : 'Koyu temaya geç'}
	onclick={() => session.setTheme(session.theme === 'dark' ? 'light' : 'dark')}
>
	{#if session.theme === 'dark'}<SunIcon />{:else}<MoonIcon />{/if}
</Button>
