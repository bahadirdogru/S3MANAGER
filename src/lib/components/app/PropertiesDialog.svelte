<script lang="ts">
	import { writeText } from '@tauri-apps/plugin-clipboard-manager';
	import { toast } from 'svelte-sonner';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import XIcon from '@lucide/svelte/icons/x';
	import CopyIcon from '@lucide/svelte/icons/copy';
	import Loader2Icon from '@lucide/svelte/icons/loader-2';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Label } from '#lib/components/ui/label/index.js';
	import { Switch } from '#lib/components/ui/switch/index.js';
	import { api, errorText, type ObjectInfo } from '#lib/api.js';
	import { formatDate, formatSize } from '#lib/format.js';
	import { explorer } from '#lib/stores/explorer.svelte.js';
	import { session } from '#lib/stores/session.svelte.js';
	import { ui } from '#lib/stores/ui.svelte.js';

	let info = $state<ObjectInfo | null>(null);
	let loading = $state(false);
	let saving = $state(false);
	let error = $state<string | null>(null);

	let contentType = $state('');
	let cacheControl = $state('');
	let contentDisposition = $state('');
	let isPublic = $state(false);
	let meta = $state<{ k: string; v: string }[]>([]);

	$effect(() => {
		const item = ui.properties;
		info = null;
		error = null;
		if (!item) return;
		loading = true;
		api
			.objectInfo(item.path)
			.then((r) => {
				if (ui.properties !== item) return;
				info = r;
				contentType = r.contentType;
				cacheControl = r.cacheControl;
				contentDisposition = r.contentDisposition;
				isPublic = r.acl === 'public-read';
				meta = Object.entries(r.metadata).map(([k, v]) => ({ k, v }));
			})
			.catch((e) => (error = errorText(e)))
			.finally(() => (loading = false));
	});

	const metaRecord = $derived(
		Object.fromEntries(meta.filter((m) => m.k.trim()).map((m) => [m.k.trim().toLowerCase(), m.v]))
	);
	const metaDirty = $derived(
		!!info &&
			(contentType !== info.contentType ||
				cacheControl !== info.cacheControl ||
				contentDisposition !== info.contentDisposition ||
				JSON.stringify(metaRecord) !== JSON.stringify(info.metadata))
	);
	const aclDirty = $derived(!!info && isPublic !== (info.acl === 'public-read'));

	const publicUrl = $derived.by(() => {
		const c = session.credentials;
		if (!c || !info) return '';
		const u = new URL(c.endpoint);
		const key = info.key.split('/').map(encodeURIComponent).join('/');
		return c.pathStyle ? `${u.origin}/${c.bucket}/${key}` : `${u.protocol}//${c.bucket}.${u.host}/${key}`;
	});

	async function save() {
		if (!info) return;
		saving = true;
		try {
			if (metaDirty) {
				await api.updateMetadata(info.key, { contentType, cacheControl, contentDisposition, metadata: metaRecord });
			}
			if (aclDirty) {
				const acl = isPublic ? 'public-read' : 'private';
				await api.setAcl([info.key], acl);
				explorer.acls.set(info.key, acl);
			}
			toast.success('Özellikler kaydedildi');
			ui.properties = null;
		} catch (e) {
			toast.error(errorText(e));
		} finally {
			saving = false;
		}
	}
</script>

<Dialog.Root open={!!ui.properties} onOpenChange={(o) => !o && (ui.properties = null)}>
	<Dialog.Content class="sm:max-w-xl">
		<Dialog.Header>
			<Dialog.Title>Özellikler</Dialog.Title>
			<Dialog.Description class="truncate" title={ui.properties?.path}>{ui.properties?.path}</Dialog.Description>
		</Dialog.Header>

		{#if loading}
			<div class="text-muted-foreground flex items-center gap-2 text-sm"><Loader2Icon class="size-4 animate-spin" /> Yükleniyor…</div>
		{:else if error}
			<p class="text-destructive text-sm" data-selectable>{error}</p>
		{:else if info}
			<div class="text-muted-foreground grid grid-cols-[7rem_1fr] gap-x-3 gap-y-1 text-xs" data-selectable>
				<span>Boyut</span><span class="text-foreground">{formatSize(info.contentLength)} ({info.contentLength.toLocaleString('tr-TR')} bayt)</span>
				<span>Değiştirilme</span><span class="text-foreground">{formatDate(info.lastModified)}</span>
				<span>ETag</span><span class="text-foreground font-mono break-all">{info.etag}</span>
			</div>

			<div class="grid gap-3">
				<label class="flex items-center justify-between rounded-md border p-3 text-sm">
					<span>
						Herkese açık (public-read)
						<span class="text-muted-foreground block text-xs">Kapalıyken yalnızca imzalı linkle erişilebilir.</span>
					</span>
					<Switch bind:checked={isPublic} />
				</label>
				{#if info.acl === 'public-read'}
					<div class="flex items-center gap-2">
						<Input readonly value={publicUrl} class="h-8 font-mono text-xs" />
						<Button size="icon-sm" variant="outline" title="Kopyala" onclick={() => writeText(publicUrl).then(() => toast.success('Kopyalandı'))}>
							<CopyIcon />
						</Button>
					</div>
				{/if}

				<div class="grid gap-1.5">
					<Label for="ct">Content-Type</Label>
					<Input id="ct" bind:value={contentType} class="h-8" />
				</div>
				<div class="grid grid-cols-2 gap-3">
					<div class="grid gap-1.5">
						<Label for="cc">Cache-Control</Label>
						<Input id="cc" bind:value={cacheControl} class="h-8" placeholder="max-age=86400" />
					</div>
					<div class="grid gap-1.5">
						<Label for="cd">Content-Disposition</Label>
						<Input id="cd" bind:value={contentDisposition} class="h-8" placeholder="inline" />
					</div>
				</div>

				<div class="grid gap-1.5">
					<div class="flex items-center justify-between">
						<Label>Özel metadata (x-amz-meta-*)</Label>
						<Button size="xs" variant="ghost" onclick={() => (meta = [...meta, { k: '', v: '' }])}><PlusIcon /> Ekle</Button>
					</div>
					{#each meta as m, i (i)}
						<div class="grid grid-cols-[1fr_1fr_1.75rem] gap-2">
							<Input bind:value={m.k} class="h-8" placeholder="anahtar" />
							<Input bind:value={m.v} class="h-8" placeholder="değer" />
							<Button size="icon-sm" variant="ghost" onclick={() => (meta = meta.filter((_, j) => j !== i))}><XIcon /></Button>
						</div>
					{:else}
						<p class="text-muted-foreground text-xs">Özel metadata yok.</p>
					{/each}
				</div>
			</div>
		{/if}

		<Dialog.Footer>
			<Button variant="outline" onclick={() => (ui.properties = null)}>Kapat</Button>
			<Button disabled={!info || saving || !(metaDirty || aclDirty)} onclick={save}>
				{#if saving}<Loader2Icon class="animate-spin" />{/if} Kaydet
			</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
