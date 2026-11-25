<script lang="ts">
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';
	import Loader2Icon from '@lucide/svelte/icons/loader-2';
	import { Button } from '#lib/components/ui/button/index.js';
	import { api, errorText, type Item, type Preview } from '#lib/api.js';
	import { formatDate, formatSize } from '#lib/format.js';
	import * as actions from '#lib/actions.js';

	let { item }: { item: Item | null } = $props();

	let preview = $state<Preview | null>(null);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let seq = 0;

	$effect(() => {
		const it = item;
		preview = null;
		error = null;
		if (!it || it.kind !== 'file') return;
		const mine = ++seq;
		loading = true;
		// Small debounce so arrowing/clicking through rows doesn't fire a GET each time.
		const t = setTimeout(async () => {
			try {
				const p = await api.preview(it.path, it.size);
				if (mine === seq) preview = p;
			} catch (e) {
				if (mine === seq) error = errorText(e);
			} finally {
				if (mine === seq) loading = false;
			}
		}, 150);
		return () => clearTimeout(t);
	});
</script>

<aside class="bg-card flex h-full flex-col border-l">
	{#if !item}
		<div class="text-muted-foreground grid flex-1 place-items-center p-6 text-center text-sm">
			Önizleme için bir dosya seçin.
		</div>
	{:else}
		<div class="border-b p-3">
			<div class="truncate text-sm font-medium" title={item.name} data-selectable>{item.name}</div>
			<div class="text-muted-foreground mt-0.5 text-xs">
				{formatSize(item.size)} · {formatDate(item.modified)}
			</div>
			<div class="mt-2 flex gap-1">
				<Button size="xs" variant="outline" onclick={() => actions.download([item])}>İndir</Button>
				<Button size="xs" variant="outline" onclick={() => actions.share(item, 3)}>Paylaş</Button>
				<Button size="xs" variant="outline" onclick={() => actions.properties(item)}>Özellikler</Button>
			</div>
		</div>
		<div class="min-h-0 flex-1 overflow-auto">
			{#if loading}
				<div class="text-muted-foreground grid h-full place-items-center"><Loader2Icon class="size-5 animate-spin" /></div>
			{:else if error}
				<p class="text-destructive p-3 text-sm" data-selectable>{error}</p>
			{:else if preview?.kind === 'image'}
				<div class="checker grid min-h-full place-items-center p-3">
					<img src={preview.dataUrl} alt={item.name} class="max-h-full max-w-full rounded object-contain shadow" />
				</div>
			{:else if preview?.kind === 'text'}
				<pre class="p-3 font-mono text-xs leading-relaxed break-all whitespace-pre-wrap" data-selectable>{preview.text}</pre>
				{#if preview.truncated}
					<p class="text-muted-foreground border-t p-2 text-center text-xs">İlk 256 KB gösteriliyor</p>
				{/if}
			{:else if preview}
				<div class="text-muted-foreground grid h-full place-items-center p-6 text-center text-sm">
					<div class="grid justify-items-center gap-2">
						<EyeOffIcon class="size-8 opacity-40" />
						Bu dosya türü için önizleme yok
						<span class="text-xs">{preview.mime}</span>
					</div>
				</div>
			{/if}
		</div>
	{/if}
</aside>

<style>
	.checker {
		background-image: conic-gradient(
			color-mix(in oklch, var(--muted), transparent 0%) 25%,
			transparent 0 50%,
			color-mix(in oklch, var(--muted), transparent 0%) 0 75%,
			transparent 0
		);
		background-size: 16px 16px;
	}
</style>
