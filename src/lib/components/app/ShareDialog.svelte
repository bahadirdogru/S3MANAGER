<script lang="ts">
	import { writeText } from '@tauri-apps/plugin-clipboard-manager';
	import { toast } from 'svelte-sonner';
	import CopyIcon from '@lucide/svelte/icons/copy';
	import Loader2Icon from '@lucide/svelte/icons/loader-2';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Textarea } from '#lib/components/ui/textarea/index.js';
	import { api, errorText } from '#lib/api.js';
	import { ui } from '#lib/stores/ui.svelte.js';

	let url = $state('');
	let expiresAt = $state(0);
	let error = $state<string | null>(null);
	let loading = $state(false);

	const expiry = $derived(
		expiresAt ? new Intl.DateTimeFormat('tr-TR', { dateStyle: 'long', timeStyle: 'short' }).format(expiresAt * 1000) : ''
	);

	$effect(() => {
		const req = ui.share;
		url = '';
		error = null;
		if (!req) return;
		loading = true;
		api
			.shareLink(req.item.path, req.days)
			.then(async (r) => {
				if (ui.share !== req) return;
				url = r.url;
				expiresAt = r.expiresAt;
				// The link lands on the clipboard right away.
				await writeText(r.url);
				toast.success('Paylaşım linki panoya kopyalandı');
			})
			.catch((e) => (error = errorText(e)))
			.finally(() => (loading = false));
	});

	async function copy() {
		await writeText(url);
		toast.success('Kopyalandı');
	}
</script>

<Dialog.Root open={!!ui.share} onOpenChange={(o) => !o && (ui.share = null)}>
	<Dialog.Content class="sm:max-w-lg">
		<Dialog.Header>
			<Dialog.Title>Paylaşım Linki ({ui.share?.days} gün)</Dialog.Title>
			<Dialog.Description class="truncate">{ui.share?.item.name}</Dialog.Description>
		</Dialog.Header>
		{#if loading}
			<div class="text-muted-foreground flex items-center gap-2 text-sm"><Loader2Icon class="size-4 animate-spin" /> Oluşturuluyor…</div>
		{:else if error}
			<p class="text-destructive text-sm" data-selectable>{error}</p>
		{:else if url}
			<Textarea readonly value={url} rows={4} class="font-mono text-xs break-all" onfocus={(e) => e.currentTarget.select()} />
			<p class="text-muted-foreground text-xs">Link {expiry} tarihine kadar geçerli. Linke sahip herkes dosyayı indirebilir.</p>
		{/if}
		<Dialog.Footer>
			<Button variant="outline" onclick={() => (ui.share = null)}>Kapat</Button>
			<Button disabled={!url} onclick={copy}><CopyIcon /> Kopyala</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
