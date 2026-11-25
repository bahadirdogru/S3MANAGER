<script lang="ts">
	import { onMount } from 'svelte';
	import { getCurrentWebview } from '@tauri-apps/api/webview';
	import ArrowLeftIcon from '@lucide/svelte/icons/arrow-left';
	import RefreshCwIcon from '@lucide/svelte/icons/refresh-cw';
	import UploadIcon from '@lucide/svelte/icons/upload';
	import FolderUpIcon from '@lucide/svelte/icons/folder-up';
	import FolderPlusIcon from '@lucide/svelte/icons/folder-plus';
	import DownloadIcon from '@lucide/svelte/icons/download';
	import Trash2Icon from '@lucide/svelte/icons/trash-2';
	import SettingsIcon from '@lucide/svelte/icons/settings';
	import LogOutIcon from '@lucide/svelte/icons/log-out';
	import SearchIcon from '@lucide/svelte/icons/search';
	import PanelRightIcon from '@lucide/svelte/icons/panel-right';
	import HouseIcon from '@lucide/svelte/icons/house';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Separator } from '#lib/components/ui/separator/index.js';
	import * as Breadcrumb from '#lib/components/ui/breadcrumb/index.js';
	import * as Resizable from '#lib/components/ui/resizable/index.js';
	import * as Tooltip from '#lib/components/ui/tooltip/index.js';
	import * as actions from '#lib/actions.js';
	import { explorer } from '#lib/stores/explorer.svelte.js';
	import { session } from '#lib/stores/session.svelte.js';
	import { transfers } from '#lib/stores/transfers.svelte.js';
	import { dialogs } from '#lib/stores/dialogs.svelte.js';
	import { ui } from '#lib/stores/ui.svelte.js';
	import FileTable from './FileTable.svelte';
	import PreviewPanel from './PreviewPanel.svelte';
	import TransferPanel from './TransferPanel.svelte';
	import ThemeToggle from './ThemeToggle.svelte';
	import DialogHost from './DialogHost.svelte';
	import UploadDialog from './UploadDialog.svelte';
	import ShareDialog from './ShareDialog.svelte';
	import PropertiesDialog from './PropertiesDialog.svelte';
	import SettingsDialog from './SettingsDialog.svelte';
	import ConnectionIndicator from './ConnectionIndicator.svelte';

	let searchInput = $state('');
	let searchTimer: ReturnType<typeof setTimeout> | undefined;
	let dropping = $state(false);

	const crumbs = $derived.by(() => {
		const parts = explorer.prefix.split('/').filter(Boolean);
		return parts.map((name, i) => ({ name, prefix: `${parts.slice(0, i + 1).join('/')}/` }));
	});
	const selection = $derived(explorer.selectedItems);
	const singleFile = $derived(selection.length === 1 && selection[0].kind === 'file' ? selection[0] : null);

	$effect(() => {
		// Keep the search box in sync when navigation clears the filter.
		searchInput = explorer.search;
	});

	function onSearch(v: string) {
		clearTimeout(searchTimer);
		searchTimer = setTimeout(() => explorer.setSearch(v), 300);
	}

	onMount(() => {
		const un = getCurrentWebview().onDragDropEvent((e) => {
			const p = e.payload;
			if (p.type === 'enter' || p.type === 'over') dropping = true;
			else if (p.type === 'leave') dropping = false;
			else if (p.type === 'drop') {
				dropping = false;
				void actions.uploadDropped(p.paths);
			}
		});
		return () => void un.then((f) => f());
	});

	function typing(e: KeyboardEvent) {
		const t = e.target as HTMLElement | null;
		return !!t && (t.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(t.tagName));
	}

	const anyDialog = $derived(
		!!dialogs.current || !!ui.upload || !!ui.share || !!ui.properties || ui.settings
	);

	function onKeydown(e: KeyboardEvent) {
		if (anyDialog || typing(e)) return;
		const mod = e.ctrlKey || e.metaKey;
		const k = e.key;
		const run = (f: () => unknown) => {
			e.preventDefault();
			void f();
		};
		if (k === 'F5' || (mod && k.toLowerCase() === 'r')) run(() => explorer.refresh());
		else if (k === 'Delete') run(() => actions.remove());
		else if (k === 'F2') run(() => actions.rename());
		else if (mod && k.toLowerCase() === 'a') run(() => explorer.selectAll());
		else if (mod && k.toLowerCase() === 'c') run(() => actions.copyTo());
		else if (mod && k.toLowerCase() === 'x') run(() => actions.moveTo());
		else if (mod && k.toLowerCase() === 'u') run(() => actions.pickUploadFiles());
		else if (mod && e.shiftKey && k.toLowerCase() === 'n') run(() => actions.newFolder());
		else if (mod && k.toLowerCase() === 'f') run(() => document.getElementById('search')?.focus());
		else if (k === 'Escape') run(() => explorer.clearSelection());
		else if (k === 'Backspace' || (e.altKey && k === 'ArrowLeft')) run(() => explorer.back());
		else if (k === 'Enter' && selection.length === 1) {
			const it = selection[0];
			run(() => (it.kind === 'folder' ? explorer.open(it.path) : actions.properties(it)));
		}
	}
</script>

<svelte:window onkeydown={onKeydown} />

{#snippet tool(label: string, shortcut: string, Icon: typeof UploadIcon, onclick: () => unknown, disabled = false)}
	<Tooltip.Root>
		<Tooltip.Trigger>
			{#snippet child({ props })}
				<Button {...props} variant="ghost" size="sm" {disabled} onclick={() => void onclick()}>
					<Icon />
					<span class="hidden xl:inline">{label}</span>
				</Button>
			{/snippet}
		</Tooltip.Trigger>
		<Tooltip.Content>{label}{shortcut ? ` (${shortcut})` : ''}</Tooltip.Content>
	</Tooltip.Root>
{/snippet}

<div class="flex h-full flex-col">
	<!-- Toolbar -->
	<header class="bg-card flex h-12 shrink-0 items-center gap-1 border-b px-2">
		<div class="flex items-center gap-2 pr-2 pl-1">
			<ConnectionIndicator />
			<div class="leading-tight">
				<div class="max-w-40 truncate text-sm font-semibold">{session.credentials?.bucket}</div>
				<div class="text-muted-foreground max-w-40 truncate text-[11px]">
					{session.credentials?.endpoint.replace(/^https?:\/\//, '')}
				</div>
			</div>
		</div>
		<Separator orientation="vertical" class="mx-1 h-6" />
		{@render tool('Dosya Yükle', 'Ctrl+U', UploadIcon, actions.pickUploadFiles)}
		{@render tool('Klasör Yükle', '', FolderUpIcon, actions.pickUploadFolder)}
		{@render tool('Yeni Klasör', 'Ctrl+Shift+N', FolderPlusIcon, actions.newFolder)}
		{@render tool('İndir', '', DownloadIcon, () => actions.download(), !selection.length)}
		{@render tool('Sil', 'Del', Trash2Icon, () => actions.remove(), !selection.length)}
		<div class="flex-1"></div>
		<div class="relative w-56">
			<SearchIcon class="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2" />
			<Input
				id="search"
				class="h-8 pl-8"
				placeholder="Bu klasörde ara (önek)"
				bind:value={searchInput}
				oninput={(e) => onSearch(e.currentTarget.value)}
				onkeydown={(e) => {
					if (e.key === 'Escape') {
						searchInput = '';
						onSearch('');
						e.currentTarget.blur();
					}
				}}
			/>
		</div>
		<Separator orientation="vertical" class="mx-1 h-6" />
		<Button
			variant="ghost"
			size="icon-sm"
			title="Önizleme paneli"
			aria-pressed={ui.previewOpen}
			class={ui.previewOpen ? 'text-primary' : ''}
			onclick={() => (ui.previewOpen = !ui.previewOpen)}
		>
			<PanelRightIcon />
		</Button>
		<ThemeToggle />
		<Button variant="ghost" size="icon-sm" title="Ayarlar" onclick={() => ui.openSettings()}>
			<SettingsIcon />
		</Button>
		<Button
			variant="ghost"
			size="icon-sm"
			title="Bağlantıyı kes"
			onclick={async () => {
				if (
					transfers.active.length &&
					!(await dialogs.confirm({
						title: 'Bağlantı kesilsin mi?',
						description: `${transfers.active.length} aktif transfer iptal edilecek.`,
						confirmText: 'Bağlantıyı kes',
						destructive: true
					}))
				)
					return;
				await session.disconnect();
			}}
		>
			<LogOutIcon />
		</Button>
	</header>

	<!-- Path bar -->
	<div class="flex h-10 shrink-0 items-center gap-1 border-b px-2">
		<Button variant="ghost" size="icon-sm" title="Geri (Backspace)" disabled={!explorer.canGoBack} onclick={() => explorer.back()}>
			<ArrowLeftIcon />
		</Button>
		<Button variant="ghost" size="icon-sm" title="Yenile (F5)" onclick={() => explorer.refresh()}>
			<RefreshCwIcon class={explorer.loading ? 'animate-spin' : ''} />
		</Button>
		<Breadcrumb.Root class="min-w-0 flex-1 overflow-hidden px-1">
			<Breadcrumb.List class="flex-nowrap">
				<Breadcrumb.Item>
					<Breadcrumb.Link class="flex cursor-pointer items-center gap-1" onclick={() => explorer.open('')}>
						<HouseIcon class="size-3.5" /> root
					</Breadcrumb.Link>
				</Breadcrumb.Item>
				{#each crumbs as c, i (c.prefix)}
					<Breadcrumb.Separator />
					<Breadcrumb.Item class="min-w-0">
						{#if i === crumbs.length - 1}
							<Breadcrumb.Page class="truncate">{c.name}</Breadcrumb.Page>
						{:else}
							<Breadcrumb.Link class="cursor-pointer truncate" onclick={() => explorer.open(c.prefix)}>{c.name}</Breadcrumb.Link>
						{/if}
					</Breadcrumb.Item>
				{/each}
			</Breadcrumb.List>
		</Breadcrumb.Root>
	</div>

	<!-- Content -->
	<div class="relative min-h-0 flex-1">
		<Resizable.PaneGroup direction="horizontal" autoSaveId="s3m-main">
			<Resizable.Pane defaultSize={70} minSize={40}>
				<FileTable />
			</Resizable.Pane>
			{#if ui.previewOpen}
				<Resizable.Handle withHandle />
				<Resizable.Pane defaultSize={30} minSize={18} maxSize={55}>
					<PreviewPanel item={singleFile ?? explorer.focused} />
				</Resizable.Pane>
			{/if}
		</Resizable.PaneGroup>

		{#if dropping}
			<div class="bg-primary/10 border-primary pointer-events-none absolute inset-2 grid place-items-center rounded-xl border-2 border-dashed">
				<div class="bg-card rounded-lg px-4 py-2 text-sm shadow">
					Bırakın: <span class="font-medium">/{explorer.prefix}</span> klasörüne yüklenecek
				</div>
			</div>
		{/if}
	</div>

	<TransferPanel />

	<!-- Status bar -->
	<footer class="text-muted-foreground bg-card flex h-7 shrink-0 items-center gap-3 border-t px-3 text-xs">
		<span>{explorer.folderCount} klasör, {explorer.fileCount} dosya{explorer.nextToken ? '+' : ''}</span>
		{#if selection.length}<span>· {selection.length} seçili</span>{/if}
		{#if ui.busy}<span class="text-primary">· {ui.busy}…</span>{/if}
		<div class="flex-1"></div>
		<span>v{session.version}</span>
	</footer>
</div>

<DialogHost />
<UploadDialog />
<ShareDialog />
<PropertiesDialog />
<SettingsDialog />
