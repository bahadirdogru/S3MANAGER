<script lang="ts">
	import * as Tooltip from '#lib/components/ui/tooltip/index.js';
	import { session } from '#lib/stores/session.svelte.js';

	const c = $derived(session.credentials);
</script>

<Tooltip.Root>
	<Tooltip.Trigger>
		<span
			class="block size-2.5 rounded-full {session.online
				? 'bg-success shadow-[0_0_0_3px_color-mix(in_oklch,var(--success),transparent_75%)]'
				: 'bg-destructive'}"
			aria-label={session.online ? 'Bağlı' : 'Bağlantı yok'}
		></span>
	</Tooltip.Trigger>
	<Tooltip.Content>
		<div class="grid gap-0.5 text-xs">
			<span class="font-medium">{session.online ? 'Bağlı' : 'Bağlantı sorunu'}</span>
			{#if c}
				<span>Bucket: {c.bucket}</span>
				<span>Bölge: {c.region}</span>
				<span>Endpoint: {c.endpoint}</span>
			{/if}
		</div>
	</Tooltip.Content>
</Tooltip.Root>
