import { SvelteMap, SvelteSet } from 'svelte/reactivity';
import { api, errorText, type Acl, type Item } from '#lib/api.js';

const CACHE_TTL_MS = 60_000;
const PAGE_SIZE = 200;
const ACL_BATCH_MS = 120;

type SortKey = 'name' | 'size' | 'modified';
interface CacheEntry {
	ts: number;
	items: Item[];
	nextToken: string | null;
}

/** Folder browsing state: listing, paging, selection, sorting and lazy ACLs. */
class Explorer {
	prefix = $state('');
	search = $state('');
	items = $state<Item[]>([]);
	nextToken = $state<string | null>(null);
	loading = $state(false);
	loadingMore = $state(false);
	error = $state<string | null>(null);
	sortKey = $state<SortKey>('name');
	sortDir = $state<1 | -1>(1);
	selected = new SvelteSet<string>();
	acls = new SvelteMap<string, Acl>();
	/** Row the preview panel shows (last clicked file). */
	focused = $state<Item | null>(null);

	#history: string[] = [];
	#cache = new Map<string, CacheEntry>();
	#generation = 0;
	#anchor: string | null = null;
	#aclQueue = new Set<string>();
	#aclTimer: ReturnType<typeof setTimeout> | null = null;

	sorted = $derived.by(() => {
		const dir = this.sortDir;
		const key = this.sortKey;
		const cmpName = (a: Item, b: Item) => a.name.localeCompare(b.name, 'tr', { numeric: true, sensitivity: 'base' });
		return [...this.items].sort((a, b) => {
			if (a.kind !== b.kind) return a.kind === 'folder' ? -1 : 1;
			let r = 0;
			if (key === 'size') r = a.size - b.size;
			else if (key === 'modified') r = (a.modified ?? 0) - (b.modified ?? 0);
			return (r || cmpName(a, b)) * dir;
		});
	});

	selectedItems = $derived(this.items.filter((i) => this.selected.has(i.path)));
	canGoBack = $derived(this.prefix !== '');
	fileCount = $derived(this.items.filter((i) => i.kind === 'file').length);
	folderCount = $derived(this.items.length - this.fileCount);

	#cacheKey(prefix: string, search: string) {
		return `${prefix}\u0000${search}`;
	}

	reset() {
		this.#generation++;
		this.prefix = '';
		this.search = '';
		this.items = [];
		this.nextToken = null;
		this.error = null;
		this.selected.clear();
		this.acls.clear();
		this.focused = null;
		this.#history = [];
		this.#cache.clear();
	}

	async open(prefix: string, opts: { history?: boolean; useCache?: boolean } = {}) {
		const { history = true, useCache = true } = opts;
		if (history && prefix !== this.prefix) this.#history.push(this.prefix);
		if (prefix !== this.prefix) this.search = '';
		this.prefix = prefix;
		this.selected.clear();
		this.focused = null;
		this.#anchor = null;
		await this.#load(useCache);
	}

	async #load(useCache: boolean) {
		const gen = ++this.#generation;
		const key = this.#cacheKey(this.prefix, this.search);
		const hit = this.#cache.get(key);
		if (useCache && hit && Date.now() - hit.ts < CACHE_TTL_MS) {
			this.items = hit.items;
			this.nextToken = hit.nextToken;
			this.error = null;
			return;
		}
		this.loading = true;
		this.error = null;
		try {
			const page = await api.listPage(this.prefix, null, this.search, PAGE_SIZE);
			if (gen !== this.#generation) return; // user navigated away meanwhile
			this.items = page.items;
			this.nextToken = page.nextToken;
			this.#store();
		} catch (e) {
			if (gen !== this.#generation) return;
			this.items = [];
			this.nextToken = null;
			this.error = errorText(e);
		} finally {
			if (gen === this.#generation) this.loading = false;
		}
	}

	async loadMore() {
		if (!this.nextToken || this.loadingMore || this.loading) return;
		const gen = this.#generation;
		this.loadingMore = true;
		try {
			const page = await api.listPage(this.prefix, this.nextToken, this.search, PAGE_SIZE);
			if (gen !== this.#generation) return;
			const seen = new Set(this.items.map((i) => i.path));
			this.items = [...this.items, ...page.items.filter((i) => !seen.has(i.path))];
			this.nextToken = page.nextToken;
			this.#store();
		} catch (e) {
			if (gen === this.#generation) this.error = errorText(e);
		} finally {
			this.loadingMore = false;
		}
	}

	#store() {
		this.#cache.set(this.#cacheKey(this.prefix, this.search), {
			ts: Date.now(),
			items: this.items,
			nextToken: this.nextToken
		});
	}

	back() {
		const prev = this.#history.pop();
		if (prev !== undefined) return this.open(prev, { history: false });
		if (this.prefix) {
			const parts = this.prefix.replace(/\/$/, '').split('/');
			parts.pop();
			return this.open(parts.length ? `${parts.join('/')}/` : '', { history: false });
		}
	}

	setSearch(q: string) {
		this.search = q;
		this.selected.clear();
		return this.#load(true);
	}

	/** Drops cached listings for `prefix` and everything below it. */
	invalidate(prefix?: string) {
		if (prefix === undefined) return this.#cache.clear();
		for (const k of this.#cache.keys()) if (k.startsWith(prefix)) this.#cache.delete(k);
	}

	refresh() {
		this.invalidate(this.prefix);
		return this.#load(false);
	}

	toggleSort(key: SortKey) {
		if (this.sortKey === key) this.sortDir = this.sortDir === 1 ? -1 : 1;
		else {
			this.sortKey = key;
			this.sortDir = 1;
		}
	}

	// ---- selection ------------------------------------------------------

	click(item: Item, e: { ctrlKey: boolean; metaKey: boolean; shiftKey: boolean }) {
		const toggle = e.ctrlKey || e.metaKey;
		if (e.shiftKey && this.#anchor) {
			const rows = this.sorted;
			const a = rows.findIndex((r) => r.path === this.#anchor);
			const b = rows.findIndex((r) => r.path === item.path);
			if (a >= 0 && b >= 0) {
				if (!toggle) this.selected.clear();
				for (const r of rows.slice(Math.min(a, b), Math.max(a, b) + 1)) this.selected.add(r.path);
			}
		} else if (toggle) {
			if (this.selected.has(item.path)) this.selected.delete(item.path);
			else this.selected.add(item.path);
			this.#anchor = item.path;
		} else {
			this.selected.clear();
			this.selected.add(item.path);
			this.#anchor = item.path;
		}
		if (item.kind === 'file') this.focused = item;
	}

	/** Right-click keeps an existing multi-selection, otherwise selects the row. */
	contextSelect(item: Item) {
		if (!this.selected.has(item.path)) {
			this.selected.clear();
			this.selected.add(item.path);
			this.#anchor = item.path;
		}
	}

	selectAll() {
		for (const i of this.items) this.selected.add(i.path);
	}

	clearSelection() {
		this.selected.clear();
	}

	// ---- ACL lazy loading ----------------------------------------------

	/** Queue an ACL lookup for a file row that became visible. */
	wantAcl(key: string) {
		if (this.acls.has(key) || this.#aclQueue.has(key)) return;
		this.#aclQueue.add(key);
		this.#aclTimer ??= setTimeout(() => this.#flushAcls(), ACL_BATCH_MS);
	}

	async #flushAcls() {
		this.#aclTimer = null;
		const keys = [...this.#aclQueue];
		this.#aclQueue.clear();
		if (!keys.length) return;
		try {
			const result = await api.getAcls(keys);
			for (const [k, v] of Object.entries(result)) this.acls.set(k, v);
		} catch {
			// ACL is cosmetic; leave the badge unknown on failure.
		}
	}
}

export const explorer = new Explorer();
