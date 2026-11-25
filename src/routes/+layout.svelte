<script lang="ts">
	import './layout.css';
	import { ModeWatcher } from 'mode-watcher';
	import { Toaster } from '#lib/components/ui/sonner/index.js';
	import * as Tooltip from '#lib/components/ui/tooltip/index.js';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();
</script>

<svelte:head>
	<title>S3MANAGER</title>
</svelte:head>

<ModeWatcher defaultMode="dark" disableTransitions />
<Toaster richColors position="bottom-right" />
<Tooltip.Provider delayDuration={400}>
	{@render children()}
</Tooltip.Provider>
