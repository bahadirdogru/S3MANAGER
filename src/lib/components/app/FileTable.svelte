<script lang="ts">
	import FolderIcon from '@lucide/svelte/icons/folder';
	import FileIcon from '@lucide/svelte/icons/file';
	import FileImageIcon from '@lucide/svelte/icons/file-image';
	import FileTextIcon from '@lucide/svelte/icons/file-text';
	import FileCodeIcon from '@lucide/svelte/icons/file-code';
	import FileArchiveIcon from '@lucide/svelte/icons/file-archive';
	import FileVideoIcon from '@lucide/svelte/icons/file-video';
	import FileAudioIcon from '@lucide/svelte/icons/file-audio';
	import ArrowUpIcon from '@lucide/svelte/icons/arrow-up';
	import ArrowDownIcon from '@lucide/svelte/icons/arrow-down';
	import GlobeIcon from '@lucide/svelte/icons/globe';
	import LockIcon from '@lucide/svelte/icons/lock';
	import Loader2Icon from '@lucide/svelte/icons/loader-2';
	import FolderOpenIcon from '@lucide/svelte/icons/folder-open';
	import * as ContextMenu from '#lib/components/ui/context-menu/index.js';
	import { Skeleton } from '#lib/components/ui/skeleton/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as actions from '#lib/actions.js';
	import type { Item } from '#lib/api.js';
	import { extensionOf, formatDate, formatSize } from '#lib/format.js';
	import { explorer } from '#lib/stores/explorer.svelte.js';

	const IMAGE = new Set(['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'ico', 'bmp', 'avif']);
	const CODE = new Set(['html', 'htm', 'css', 'js', 'mjs', 'ts', 'json', 'xml', 'py', 'rs', 'go', 'sh', 'yml', 'yaml', 'toml']);
	const TEXT = new Set(['txt', 'md', 'csv', 'log', 'ini', 'pdf']);
	const ARCHIVE = new Set(['zip', 'gz', 'tar', 'bz2', '7z', 'rar', 'xz', 'iso']);
	const VIDEO = new Set(['mp4', 'mov', 'mkv', 'webm', 'avi']);
	const AUDIO = new Set(['mp3', 'wav', 'flac', 'ogg', 'm4a']);

	function iconFor(item: Item) {
		if (item.kind === 'folder') return FolderIcon;
		const ext = extensionOf(item.name);
		if (IMAGE.has(ext)) return FileImageIcon;
		if (CODE.has(ext)) return FileCodeIcon;
		if (TEXT.has(ext)) return FileTextIcon;
		if (ARCHIVE.has(ext)) return FileArchiveIcon;
		if (VIDEO.has(ext)) return FileVideoIcon;
		if (AUDIO.has(ext)) return FileAudioIcon;
		return FileIcon;
	}

	// One shared observer: queue ACL lookups only for rows that scroll into view,
	// and page in more results when the sentinel row appears. Created lazily so
	// rows mounted before any effect runs are still observed. A null root still
	// respects clipping by the scroll container.
	let observer: IntersectionObserver | null = null;
	function getObserver() {
		observer ??= new IntersectionObserver(
			(entries) => {
				for (const e of entries) {
					if (!e.isIntersecting) continue;
					const el = e.target as HTMLElement;
					if (el.dataset.sentinel) void explorer.loadMore();
					else if (el.dataset.key) explorer.wantAcl(el.dataset.key);
				}
			},
			{ rootMargin: '200px 0px' }
		);
		return observer;
	}
	$effect(() => () => observer?.disconnect());

	function observe(node: HTMLElement) {
		getObserver().observe(node);
		return { destroy: () => observer?.unobserve(node) };
	}

	function activate(item: Item) {
		if (item.kind === 'folder') void explorer.open(item.path);
		else actions.properties(item);
	}

	const sel = $derived(explorer.selectedItems);
	const single = $derived(sel.length === 1 ? sel[0] : null);

	const columns = 'grid-cols-[minmax(0,1fr)_7rem_10rem_7.5rem]';
</script>

{#snippet sortHeader(key: 'name' | 'size' | 'modified', label: string, cls = '')}
	<button
		class="hover:text-foreground flex items-center gap-1 {cls}"
		onclick={() => explorer.toggleSort(key)}
	>
		{label}
		{#if explorer.sortKey === key}
			{#if explorer.sortDir === 1}<ArrowUpIcon class="size-3" />{:else}<ArrowDownIcon class="size-3" />{/if}
		{/if}
	</button>
{/snippet}

<div class="flex h-full flex-col">
	<div
		class="text-muted-foreground bg-muted/40 grid {columns} h-8 shrink-0 items-center gap-3 border-b px-3 text-xs font-medium"
	>
		{@render sortHeader('name', 'Ad')}
		{@render sortHeader('size', 'Boyut', 'justify-end')}
		{@render sortHeader('modified', 'Değiştirilme')}
		<span>Erişim</span>
	</div>

	<ContextMenu.Root>
		<ContextMenu.Trigger class="min-h-0 flex-1">
			<div
				class="h-full overflow-auto"
				role="grid"
				tabindex="-1"
				oncontextmenu={(e) => {
					if (!(e.target as HTMLElement).closest('[data-row]')) explorer.clearSelection();
				}}
				onclick={(e) => {
					if (!(e.target as HTMLElement).closest('[data-row]')) explorer.clearSelection();
				}}
				onkeydown={() => {}}
			>
				{#if explorer.loading && !explorer.items.length}
					<div class="grid gap-2 p-3">
						{#each { length: 8 } as _, i (i)}
							<Skeleton class="h-7 w-full" />
						{/each}
					</div>
				{:else if explorer.error}
					<div class="grid h-full place-items-center p-6 text-center">
						<div class="grid gap-3">
							<p class="text-destructive text-sm" data-selectable>{explorer.error}</p>
							<Button variant="outline" size="sm" onclick={() => explorer.refresh()}>Tekrar dene</Button>
						</div>
					</div>
				{:else if !explorer.items.length}
					<div class="text-muted-foreground grid h-full place-items-center p-6 text-center text-sm">
						<div class="grid justify-items-center gap-2">
							<FolderOpenIcon class="size-10 opacity-40" />
							{explorer.search ? `“${explorer.search}” ile başlayan öğe yok` : 'Bu klasör boş'}
							<span class="text-xs">Dosyaları buraya sürükleyip bırakarak yükleyebilirsiniz.</span>
						</div>
					</div>
				{:else}
					{#each explorer.sorted as item (item.path)}
						{@const Icon = iconFor(item)}
						{@const selected = explorer.selected.has(item.path)}
						{@const acl = explorer.acls.get(item.path)}
						<div
							data-row
							data-key={item.kind === 'file' ? item.path : undefined}
							use:observe
							role="row"
							tabindex="-1"
							aria-selected={selected}
							class="grid {columns} h-8 cursor-default items-center gap-3 px-3 text-sm [content-visibility:auto] [contain-intrinsic-size:auto_2rem]
								{selected ? 'bg-selected' : 'hover:bg-muted/60'}"
							onclick={(e) => explorer.click(item, e)}
							ondblclick={() => activate(item)}
							oncontextmenu={() => explorer.contextSelect(item)}
							onkeydown={() => {}}
						>
							<span class="flex min-w-0 items-center gap-2">
								<Icon class="size-4 shrink-0 {item.kind === 'folder' ? 'text-primary' : 'text-muted-foreground'}" />
								<span class="truncate" title={item.name}>{item.name}</span>
							</span>
							<span class="text-muted-foreground text-right tabular-nums">
								{item.kind === 'file' ? formatSize(item.size) : ''}
							</span>
							<span class="text-muted-foreground tabular-nums">{formatDate(item.modified)}</span>
							<span class="text-muted-foreground flex items-center gap-1 text-xs whitespace-nowrap">
								{#if item.kind === 'file'}
									{#if acl === 'public-read'}
										<GlobeIcon class="text-warning size-3.5" /> Herkese açık
									{:else if acl === 'private'}
										<LockIcon class="size-3.5" /> Özel
									{:else}
										<span class="opacity-50">…</span>
									{/if}
								{/if}
							</span>
						</div>
					{/each}
					{#if explorer.nextToken}
						<!-- Re-mounted per page so it fires again if it is still on screen. -->
						{#key explorer.nextToken}
							<div data-sentinel="1" use:observe class="text-muted-foreground flex h-10 items-center justify-center gap-2 text-xs">
								<Loader2Icon class="size-3.5 animate-spin" /> Daha fazla yükleniyor…
							</div>
						{/key}
					{/if}
				{/if}
			</div>
		</ContextMenu.Trigger>

		<ContextMenu.Content class="w-56">
			{#if sel.length}
				{#if single?.kind === 'folder'}
					<ContextMenu.Item onclick={() => explorer.open(single.path)}>Aç</ContextMenu.Item>
				{/if}
				<ContextMenu.Item onclick={() => actions.download()}>
					{sel.length > 1 ? `Seçilenleri İndir (${sel.length})` : 'İndir'}
				</ContextMenu.Item>
				{#if single?.kind === 'file'}
					<ContextMenu.Item onclick={() => actions.share(single, 3)}>Paylaş (3 Gün)</ContextMenu.Item>
					<ContextMenu.Item onclick={() => actions.share(single, 7)}>Paylaş (7 Gün)</ContextMenu.Item>
					<ContextMenu.Item onclick={() => actions.properties(single)}>
						Özellikler <ContextMenu.Shortcut>Enter</ContextMenu.Shortcut>
					</ContextMenu.Item>
				{/if}
				<ContextMenu.Separator />
				{#if single}
					<ContextMenu.Item onclick={() => actions.rename(single)}>
						Yeniden Adlandır <ContextMenu.Shortcut>F2</ContextMenu.Shortcut>
					</ContextMenu.Item>
				{/if}
				<ContextMenu.Item onclick={() => actions.copyTo()}>
					Kopyala… <ContextMenu.Shortcut>Ctrl+C</ContextMenu.Shortcut>
				</ContextMenu.Item>
				<ContextMenu.Item onclick={() => actions.moveTo()}>
					Taşı… <ContextMenu.Shortcut>Ctrl+X</ContextMenu.Shortcut>
				</ContextMenu.Item>
				<ContextMenu.Separator />
				<ContextMenu.Item variant="destructive" onclick={() => actions.remove()}>
					{sel.length > 1 ? `Seçilenleri Sil (${sel.length})` : 'Sil'}
					<ContextMenu.Shortcut>Del</ContextMenu.Shortcut>
				</ContextMenu.Item>
				<ContextMenu.Separator />
			{/if}
			<ContextMenu.Item onclick={() => actions.newFolder()}>Yeni Klasör</ContextMenu.Item>
			<ContextMenu.Item onclick={() => actions.pickUploadFiles()}>Dosya Yükle</ContextMenu.Item>
			<ContextMenu.Item onclick={() => actions.pickUploadFolder()}>Klasör Yükle</ContextMenu.Item>
			<ContextMenu.Separator />
			<ContextMenu.Item onclick={() => explorer.selectAll()}>
				Tümünü Seç <ContextMenu.Shortcut>Ctrl+A</ContextMenu.Shortcut>
			</ContextMenu.Item>
			{#if sel.length}
				<ContextMenu.Item onclick={() => explorer.clearSelection()}>
					Seçimi Bırak <ContextMenu.Shortcut>Esc</ContextMenu.Shortcut>
				</ContextMenu.Item>
			{/if}
			<ContextMenu.Item onclick={() => explorer.refresh()}>
				Yenile <ContextMenu.Shortcut>F5</ContextMenu.Shortcut>
			</ContextMenu.Item>
		</ContextMenu.Content>
	</ContextMenu.Root>
</div>
