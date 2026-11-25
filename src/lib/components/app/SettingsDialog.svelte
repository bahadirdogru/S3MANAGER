<script lang="ts">
	import { openUrl, revealItemInDir } from '@tauri-apps/plugin-opener';
	import { toast } from 'svelte-sonner';
	import Loader2Icon from '@lucide/svelte/icons/loader-2';
	import RefreshCwIcon from '@lucide/svelte/icons/refresh-cw';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import * as Tabs from '#lib/components/ui/tabs/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Label } from '#lib/components/ui/label/index.js';
	import { Switch } from '#lib/components/ui/switch/index.js';
	import { api, errorText, type MultipartInfo, type UpdateInfo, type UploadMetadataSettings } from '#lib/api.js';
	import { formatDate } from '#lib/format.js';
	import { dialogs } from '#lib/stores/dialogs.svelte.js';
	import { session } from '#lib/stores/session.svelte.js';
	import { ui } from '#lib/stores/ui.svelte.js';

	// ---- metadata tab
	let meta = $state<UploadMetadataSettings | null>(null);
	let inlineCsv = $state('');
	let attachCsv = $state('');

	// ---- log tab
	let log = $state<{ path: string; text: string } | null>(null);

	// ---- maintenance tab
	let uploads = $state<MultipartInfo[] | null>(null);
	let uploadsLoading = $state(false);

	// ---- about tab
	let update = $state<UpdateInfo | null>(null);
	let checking = $state(false);

	const csv = (list: string[]) => [...list].sort().join(', ');
	const parse = (s: string) => [...new Set(s.split(',').map((p) => p.trim().replace(/^\./, '').toLowerCase()).filter(Boolean))];

	$effect(() => {
		if (!ui.settings) return;
		api.getUploadMetadata().then((m) => {
			meta = m;
			inlineCsv = csv(m.inlineExtensions);
			attachCsv = csv(m.attachmentExtensions);
		});
	});

	$effect(() => {
		if (!ui.settings) return;
		if (ui.settingsTab === 'log') void loadLog();
		if (ui.settingsTab === 'maintenance' && uploads === null) void loadUploads();
	});

	async function saveMeta() {
		if (!meta) return;
		try {
			await api.saveUploadMetadata({ ...meta, inlineExtensions: parse(inlineCsv), attachmentExtensions: parse(attachCsv) });
			toast.success('Metadata ayarları kaydedildi');
		} catch (e) {
			toast.error(errorText(e));
		}
	}

	async function resetMeta() {
		meta = {
			enabled: true,
			cacheControl: '',
			textCharset: 'utf-8',
			inlineExtensions: ['css', 'gif', 'htm', 'html', 'ico', 'jpeg', 'jpg', 'js', 'json', 'mjs', 'pdf', 'png', 'svg', 'txt', 'webp', 'xml'],
			attachmentExtensions: ['7z', 'bin', 'bz2', 'exe', 'gz', 'iso', 'msi', 'rar', 'tar', 'zip']
		};
		inlineCsv = csv(meta.inlineExtensions);
		attachCsv = csv(meta.attachmentExtensions);
	}

	async function loadLog() {
		log = await api.readLog(500);
	}

	async function loadUploads() {
		uploadsLoading = true;
		try {
			uploads = await api.listMultipart();
		} catch (e) {
			toast.error(errorText(e));
		} finally {
			uploadsLoading = false;
		}
	}

	async function abort(u: MultipartInfo[]) {
		if (!u.length) return;
		const ok = await dialogs.confirm({
			title: u.length === 1 ? 'Yarım yükleme iptal edilsin mi?' : `${u.length} yarım yükleme iptal edilsin mi?`,
			description: 'Yüklenmiş parçalar silinir ve depolama alanı boşaltılır.',
			confirmText: 'İptal et',
			destructive: true
		});
		if (!ok) return;
		let n = 0;
		for (const x of u) {
			try {
				await api.abortMultipart(x.key, x.uploadId);
				n++;
			} catch (e) {
				toast.error(errorText(e));
			}
		}
		toast.success(`${n} yarım yükleme temizlendi`);
		await loadUploads();
	}

	async function checkUpdate() {
		checking = true;
		try {
			update = await api.checkUpdate();
			if (!update.newer) toast.success('Güncelsiniz');
		} catch (e) {
			toast.error(errorText(e));
		} finally {
			checking = false;
		}
	}
</script>

<Dialog.Root bind:open={ui.settings}>
	<Dialog.Content class="sm:max-w-3xl">
		<Dialog.Header>
			<Dialog.Title>Ayarlar</Dialog.Title>
		</Dialog.Header>

		<Tabs.Root bind:value={ui.settingsTab} class="min-h-[26rem]">
			<Tabs.List class="w-full">
				<Tabs.Trigger value="connection">Bağlantı</Tabs.Trigger>
				<Tabs.Trigger value="metadata">Metadata</Tabs.Trigger>
				<Tabs.Trigger value="appearance">Görünüm</Tabs.Trigger>
				<Tabs.Trigger value="log">Günlük</Tabs.Trigger>
				<Tabs.Trigger value="maintenance">Bakım</Tabs.Trigger>
				<Tabs.Trigger value="about">Hakkında</Tabs.Trigger>
			</Tabs.List>

			<Tabs.Content value="connection" class="grid content-start gap-4 pt-3">
				{#if session.credentials}
					<div class="grid grid-cols-[8rem_1fr] gap-x-3 gap-y-2 text-sm" data-selectable>
						<span class="text-muted-foreground">Bucket</span><span>{session.credentials.bucket}</span>
						<span class="text-muted-foreground">Bölge</span><span>{session.credentials.region}</span>
						<span class="text-muted-foreground">Endpoint</span><span>{session.credentials.endpoint}</span>
						<span class="text-muted-foreground">Adresleme</span><span>{session.credentials.pathStyle ? 'Path-style' : 'Virtual-host'}</span>
						<span class="text-muted-foreground">Access key</span><span class="font-mono">{session.credentials.key.slice(0, 6)}…</span>
						<span class="text-muted-foreground">Ayar dosyası</span><span class="font-mono text-xs">{session.configDir}/config.ini</span>
					</div>
					<div class="flex gap-2">
						<Button
							variant="outline"
							onclick={async () => {
								ui.settings = false;
								await session.disconnect();
							}}>Bağlantıyı değiştir</Button
						>
						<Button variant="ghost" onclick={() => revealItemInDir(`${session.configDir}/config.ini`)}>Klasörü aç</Button>
					</div>
				{/if}
			</Tabs.Content>

			<Tabs.Content value="metadata" class="grid content-start gap-4 pt-3">
				{#if meta}
					<label class="flex items-center justify-between rounded-md border p-3 text-sm">
						<span>
							Otomatik metadata
							<span class="text-muted-foreground block text-xs">Yüklemede Content-Type, Content-Disposition ve Cache-Control ekle.</span>
						</span>
						<Switch bind:checked={meta.enabled} />
					</label>
					<fieldset class="grid gap-4 disabled:opacity-50" disabled={!meta.enabled}>
						<div class="grid grid-cols-2 gap-3">
							<div class="grid gap-1.5">
								<Label for="cache">Cache-Control</Label>
								<Input id="cache" bind:value={meta.cacheControl} placeholder="ör. public, max-age=86400" />
							</div>
							<div class="grid gap-1.5">
								<Label for="charset">Metin karakter seti</Label>
								<Input id="charset" bind:value={meta.textCharset} placeholder="utf-8" />
							</div>
						</div>
						<div class="grid gap-1.5">
							<Label for="inline">Tarayıcıda açılacak uzantılar (inline)</Label>
							<Input id="inline" bind:value={inlineCsv} />
						</div>
						<div class="grid gap-1.5">
							<Label for="attach">İndirilecek uzantılar (attachment)</Label>
							<Input id="attach" bind:value={attachCsv} />
						</div>
					</fieldset>
					<div class="flex gap-2">
						<Button onclick={saveMeta}>Kaydet</Button>
						<Button variant="ghost" onclick={resetMeta}>Varsayılanlar</Button>
					</div>
				{/if}
			</Tabs.Content>

			<Tabs.Content value="appearance" class="grid content-start gap-4 pt-3">
				<label class="flex items-center justify-between rounded-md border p-3 text-sm">
					<span>Koyu tema</span>
					<Switch checked={session.theme === 'dark'} onCheckedChange={(v) => session.setTheme(v ? 'dark' : 'light')} />
				</label>
			</Tabs.Content>

			<Tabs.Content value="log" class="grid content-start gap-2 pt-3">
				<div class="flex items-center gap-2">
					<span class="text-muted-foreground flex-1 truncate font-mono text-xs">{log?.path}</span>
					<Button size="sm" variant="ghost" onclick={loadLog}><RefreshCwIcon /> Yenile</Button>
					{#if log}<Button size="sm" variant="ghost" onclick={() => log && revealItemInDir(log.path)}>Klasörde göster</Button>{/if}
				</div>
				<pre
					class="bg-muted/50 h-80 overflow-auto rounded-md border p-2 font-mono text-[11px] leading-relaxed whitespace-pre-wrap"
					data-selectable>{log?.text || 'Günlük boş.'}</pre>
			</Tabs.Content>

			<Tabs.Content value="maintenance" class="grid content-start gap-3 pt-3">
				<div class="flex items-center gap-2">
					<p class="text-muted-foreground flex-1 text-sm">
						Yarım kalmış multipart yüklemeler depolama alanı kaplar. Buradan temizleyebilirsiniz.
					</p>
					<Button size="sm" variant="ghost" onclick={loadUploads} disabled={uploadsLoading}>
						{#if uploadsLoading}<Loader2Icon class="animate-spin" />{:else}<RefreshCwIcon />{/if} Yenile
					</Button>
					<Button size="sm" variant="destructive" disabled={!uploads?.length} onclick={() => abort(uploads ?? [])}>Tümünü iptal et</Button>
				</div>
				<div class="max-h-72 overflow-auto rounded-md border">
					{#if uploads?.length}
						{#each uploads as u (u.uploadId)}
							<div class="hover:bg-muted/50 grid grid-cols-[minmax(0,1fr)_9rem_auto] items-center gap-3 px-3 py-1.5 text-xs">
								<span class="truncate" title={u.key}>{u.key}</span>
								<span class="text-muted-foreground">{formatDate(u.initiated)}</span>
								<Button size="xs" variant="ghost" onclick={() => abort([u])}>İptal et</Button>
							</div>
						{/each}
					{:else}
						<p class="text-muted-foreground p-4 text-center text-sm">{uploadsLoading ? 'Yükleniyor…' : 'Yarım yükleme yok.'}</p>
					{/if}
				</div>
			</Tabs.Content>

			<Tabs.Content value="about" class="grid content-start gap-3 pt-3 text-sm">
				<p><span class="font-semibold">S3MANAGER</span> v{session.version} — Tauri + SvelteKit</p>
				<p class="text-muted-foreground">
					DigitalOcean Spaces ve S3 uyumlu depolar için masaüstü dosya yöneticisi. Geliştirici: Bahadır Doğru. Lisans: GPL-3.0.
				</p>
				<div class="flex gap-2">
					<Button variant="outline" onclick={checkUpdate} disabled={checking}>
						{#if checking}<Loader2Icon class="animate-spin" />{/if} Güncellemeleri denetle
					</Button>
					<Button variant="ghost" onclick={() => openUrl('https://s3manager.bahadirdogru.com/')}>Web sitesi</Button>
					<Button variant="ghost" onclick={() => openUrl('https://github.com/bahadirdogru/S3MANAGER')}>GitHub</Button>
				</div>
				{#if update?.newer}
					<div class="border-primary/40 bg-primary/5 grid gap-2 rounded-md border p-3">
						<p class="font-medium">Yeni sürüm: v{update.latest}</p>
						{#if update.body}<pre class="text-muted-foreground max-h-40 overflow-auto text-xs whitespace-pre-wrap">{update.body}</pre>{/if}
						<div class="flex gap-2">
							<Button size="sm" onclick={() => update && openUrl(update.url)}>İndir</Button>
							<Button size="sm" variant="ghost" onclick={() => update && api.dismissUpdate(update.latest).then(() => (update = null))}>
								Bu sürümü atla
							</Button>
						</div>
					</div>
				{/if}
			</Tabs.Content>
		</Tabs.Root>
	</Dialog.Content>
</Dialog.Root>
