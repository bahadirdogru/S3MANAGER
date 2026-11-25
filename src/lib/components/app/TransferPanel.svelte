<script lang="ts">
	import { revealItemInDir } from '@tauri-apps/plugin-opener';
	import ChevronUpIcon from '@lucide/svelte/icons/chevron-up';
	import ChevronDownIcon from '@lucide/svelte/icons/chevron-down';
	import XIcon from '@lucide/svelte/icons/x';
	import ArrowUpIcon from '@lucide/svelte/icons/arrow-up';
	import ArrowDownIcon from '@lucide/svelte/icons/arrow-down';
	import CheckIcon from '@lucide/svelte/icons/check';
	import CircleAlertIcon from '@lucide/svelte/icons/circle-alert';
	import BanIcon from '@lucide/svelte/icons/ban';
	import FolderSearchIcon from '@lucide/svelte/icons/folder-search';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Progress } from '#lib/components/ui/progress/index.js';
	import type { TransferEvent } from '#lib/api.js';
	import { formatSize, formatSpeed } from '#lib/format.js';
	import { transfers } from '#lib/stores/transfers.svelte.js';

	const pct = (t: TransferEvent) => (t.total ? Math.min(100, (t.transferred / t.total) * 100) : t.status === 'done' ? 100 : 0);
	const statusText: Record<TransferEvent['status'], string> = {
		queued: 'Sırada',
		running: '',
		done: 'Tamamlandı',
		error: 'Hata',
		cancelled: 'İptal edildi'
	};
</script>

{#if transfers.list.length}
	<section class="bg-card shrink-0 border-t">
		<div class="flex h-8 items-center gap-2 px-3 text-xs">
			<button class="flex items-center gap-1 font-medium" onclick={() => (transfers.panelOpen = !transfers.panelOpen)}>
				{#if transfers.panelOpen}<ChevronDownIcon class="size-3.5" />{:else}<ChevronUpIcon class="size-3.5" />{/if}
				Transferler
			</button>
			<span class="text-muted-foreground">
				{#if transfers.active.length}
					{transfers.active.length} aktif · %{transfers.overall.toFixed(0)}
				{:else}
					{transfers.list.length} tamamlandı{transfers.failed ? ` · ${transfers.failed} hata` : ''}
				{/if}
			</span>
			{#if transfers.active.length && !transfers.panelOpen}
				<Progress value={transfers.overall} class="h-1.5 w-40" />
			{/if}
			<div class="flex-1"></div>
			{#if transfers.active.length}
				<Button size="xs" variant="ghost" onclick={() => transfers.cancelAll()}>Tümünü iptal et</Button>
			{/if}
			<Button size="xs" variant="ghost" onclick={() => transfers.clearFinished()}>Bitenleri temizle</Button>
		</div>
		{#if transfers.panelOpen}
			<div class="max-h-52 overflow-auto border-t">
				{#each transfers.list as t (t.id)}
					<div class="hover:bg-muted/50 grid grid-cols-[1rem_minmax(0,1fr)_12rem_9rem_1.75rem] items-center gap-3 px-3 py-1.5 text-xs">
						{#if t.direction === 'upload'}<ArrowUpIcon class="text-primary size-3.5" />{:else}<ArrowDownIcon class="size-3.5 text-sky-500" />{/if}
						<div class="min-w-0">
							<div class="truncate" title={t.remoteKey}>{t.name}</div>
							{#if t.error}<div class="text-destructive truncate" title={t.error} data-selectable>{t.error}</div>{/if}
						</div>
						{#if t.status === 'running'}
							<Progress value={pct(t)} class="h-1.5" />
						{:else}
							<span
								class="flex items-center gap-1 {t.status === 'done'
									? 'text-success'
									: t.status === 'error'
										? 'text-destructive'
										: 'text-muted-foreground'}"
							>
								{#if t.status === 'done'}<CheckIcon class="size-3.5" />{:else if t.status === 'error'}<CircleAlertIcon class="size-3.5" />{:else if t.status === 'cancelled'}<BanIcon class="size-3.5" />{/if}
								{statusText[t.status]}
							</span>
						{/if}
						<span class="text-muted-foreground text-right tabular-nums">
							{#if t.status === 'running'}
								{formatSize(t.transferred)} / {formatSize(t.total)}
								<span class="block">{formatSpeed(t.speed)}</span>
							{:else}
								{formatSize(t.total)}
							{/if}
						</span>
						{#if t.status === 'queued' || t.status === 'running'}
							<Button size="icon-xs" variant="ghost" title="İptal" onclick={() => transfers.cancel(t.id)}><XIcon /></Button>
						{:else if t.direction === 'download' && t.status === 'done'}
							<Button size="icon-xs" variant="ghost" title="Klasörde göster" onclick={() => revealItemInDir(t.localPath)}>
								<FolderSearchIcon />
							</Button>
						{:else}
							<span></span>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	</section>
{/if}
