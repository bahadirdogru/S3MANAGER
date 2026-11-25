<script lang="ts">
	import { onMount } from 'svelte';
	import { session } from '#lib/stores/session.svelte.js';
	import { transfers } from '#lib/stores/transfers.svelte.js';
	import LoginView from '#lib/components/app/LoginView.svelte';
	import Explorer from '#lib/components/app/Explorer.svelte';

	onMount(() => {
		void session.boot();
		void transfers.init();
	});
</script>

{#if !session.ready}
	<div class="text-muted-foreground grid h-full place-items-center text-sm">Yükleniyor…</div>
{:else if session.connected}
	<Explorer />
{:else}
	<LoginView />
{/if}
