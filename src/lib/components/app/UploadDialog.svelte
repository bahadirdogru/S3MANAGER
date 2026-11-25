<script lang="ts">
	import { toast } from 'svelte-sonner';
	import XIcon from '@lucide/svelte/icons/x';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import * as Select from '#lib/components/ui/select/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Label } from '#lib/components/ui/label/index.js';
	import { api, errorText, type Acl } from '#lib/api.js';
	import { formatSize } from '#lib/format.js';
	import { explorer } from '#lib/stores/explorer.svelte.js';
	import { transfers } from '#lib/stores/transfers.svelte.js';
	import { ui } from '#lib/stores/ui.svelte.js';

	let acl = $state<Acl>('private');
	let busy = $state(false);

	const reqs = $derived(ui.upload ?? []);
	const total = $derived(reqs.reduce((s, r) => s + r.size, 0));
	const existing = $derived(new Set(explorer.items.map((i) => i.path)));
	const overwrites = $derived(reqs.filter((r) => existing.has(r.remoteKey)).length);

	function removeAt(i: number) {
		if (!ui.upload) return;
		ui.upload = ui.upload.filter((_, j) => j !== i);
		if (!ui.upload.length) ui.upload = null;
	}

	async function start() {
		if (!reqs.length) return;
		busy = true;
		try {
			transfers.add(await api.startUpload(reqs, acl));
			ui.upload = null;
		} catch (e) {
			toast.error(errorText(e));
		} finally {
			busy = false;
		}
	}
</script>

<Dialog.Root open={!!ui.upload} onOpenChange={(o) => !o && (ui.upload = null)}>
	<Dialog.Content class="sm:max-w-2xl">
		<Dialog.Header>
			<Dialog.Title>Dosya Yükle</Dialog.Title>
			<Dialog.Description>
				{reqs.length} dosya ({formatSize(total)}) → <span class="text-foreground font-medium">/{explorer.prefix}</span>
			</Dialog.Description>
		</Dialog.Header>

		<div class="max-h-72 overflow-auto rounded-md border">
			{#each reqs as r, i (r.remoteKey)}
				<div class="hover:bg-muted/50 grid grid-cols-[minmax(0,1fr)_6rem_1.5rem] items-center gap-2 px-3 py-1 text-xs">
					<span class="truncate" title={r.localPath}>
						{r.remoteKey.slice(explorer.prefix.length)}
						{#if existing.has(r.remoteKey)}<span class="text-warning ml-1">(üzerine yazılacak)</span>{/if}
					</span>
					<span class="text-muted-foreground text-right tabular-nums">{formatSize(r.size)}</span>
					<Button size="icon-xs" variant="ghost" title="Listeden çıkar" onclick={() => removeAt(i)}><XIcon /></Button>
				</div>
			{/each}
		</div>

		<div class="grid grid-cols-[auto_1fr] items-center gap-3">
			<Label>Erişim</Label>
			<Select.Root type="single" bind:value={acl}>
				<Select.Trigger class="w-56">{acl === 'private' ? 'Özel (private)' : 'Herkese açık (public-read)'}</Select.Trigger>
				<Select.Content>
					<Select.Item value="private" label="Özel (private)" />
					<Select.Item value="public-read" label="Herkese açık (public-read)" />
				</Select.Content>
			</Select.Root>
		</div>
		{#if overwrites}
			<p class="text-warning text-xs">{overwrites} dosya bu klasörde zaten var ve üzerine yazılacak.</p>
		{/if}
		<p class="text-muted-foreground text-xs">
			Content-Type, Content-Disposition ve Cache-Control Ayarlar → Metadata kurallarına göre eklenir. 16 MB üzeri dosyalar
			parçalı (multipart) yüklenir; en fazla 3 dosya paralel gönderilir.
		</p>

		<Dialog.Footer>
			<Button variant="outline" onclick={() => (ui.upload = null)}>Vazgeç</Button>
			<Button disabled={busy || !reqs.length} onclick={start}>Yüklemeyi başlat</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
