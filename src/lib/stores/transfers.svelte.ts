import { SvelteMap } from 'svelte/reactivity';
import { api, onTransfer, type TransferEvent } from '#lib/api.js';
import { explorer } from './explorer.svelte.js';

const FINISHED = new Set(['done', 'error', 'cancelled']);

/** Live transfer list fed by the backend `transfer` event. */
class Transfers {
	map = new SvelteMap<string, TransferEvent>();
	panelOpen = $state(false);
	#started = false;
	#refreshTimer: ReturnType<typeof setTimeout> | null = null;

	list = $derived([...this.map.values()].reverse());
	active = $derived(this.list.filter((t) => !FINISHED.has(t.status)));
	failed = $derived(this.list.filter((t) => t.status === 'error').length);
	overall = $derived.by(() => {
		const a = this.active;
		const total = a.reduce((s, t) => s + t.total, 0);
		const done = a.reduce((s, t) => s + t.transferred, 0);
		return total ? Math.min(100, (done / total) * 100) : 0;
	});

	async init() {
		if (this.#started) return;
		this.#started = true;
		await onTransfer((e) => {
			this.map.set(e.id, e);
			if (e.direction === 'upload' && e.status === 'done') this.#uploaded(e.remoteKey);
		});
	}

	add(events: TransferEvent[]) {
		for (const e of events) if (!this.map.has(e.id)) this.map.set(e.id, e);
		if (events.length) this.panelOpen = true;
	}

	/** Refresh the open folder (debounced) once uploads land in it. */
	#uploaded(key: string) {
		const parent = key.includes('/') ? key.slice(0, key.lastIndexOf('/') + 1) : '';
		explorer.invalidate(parent);
		if (!key.startsWith(explorer.prefix)) return;
		if (this.#refreshTimer) clearTimeout(this.#refreshTimer);
		this.#refreshTimer = setTimeout(() => explorer.refresh(), 600);
	}

	cancel(id: string) {
		return api.cancelTransfer(id);
	}

	cancelAll() {
		return api.cancelAllTransfers();
	}

	clearFinished() {
		for (const [id, t] of this.map) if (FINISHED.has(t.status)) this.map.delete(id);
	}
}

export const transfers = new Transfers();
