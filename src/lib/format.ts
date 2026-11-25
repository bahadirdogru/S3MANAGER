const UNITS = ['B', 'KB', 'MB', 'GB', 'TB'];

export function formatSize(bytes: number): string {
	if (!bytes) return '0 B';
	let i = 0;
	let n = bytes;
	while (n >= 1024 && i < UNITS.length - 1) {
		n /= 1024;
		i++;
	}
	return `${i === 0 ? n : n.toFixed(2)} ${UNITS[i]}`;
}

const dateFmt = new Intl.DateTimeFormat('tr-TR', {
	year: 'numeric',
	month: '2-digit',
	day: '2-digit',
	hour: '2-digit',
	minute: '2-digit'
});

export function formatDate(secs: number | null | undefined): string {
	return secs ? dateFmt.format(new Date(secs * 1000)) : '—';
}

export function formatSpeed(bps: number): string {
	return bps > 0 ? `${formatSize(bps)}/s` : '';
}

export function extensionOf(name: string): string {
	const i = name.lastIndexOf('.');
	return i > 0 ? name.slice(i + 1).toLowerCase() : '';
}

/** `photo.jpg` → `photo (kopya 1).jpg` (same naming as earlier releases). */
export function uniqueCopyName(name: string, existing: Set<string>): string {
	if (!existing.has(name)) return name;
	const i = name.lastIndexOf('.');
	const [base, ext] = i > 0 ? [name.slice(0, i), name.slice(i)] : [name, ''];
	for (let n = 1; ; n++) {
		const candidate = `${base} (kopya ${n})${ext}`;
		if (!existing.has(candidate)) return candidate;
	}
}

/** Normalises a user-typed folder path into an S3 prefix (`a/b/` or ``). */
export function toPrefix(input: string): string {
	const p = input.trim().replace(/\\/g, '/').replace(/^\/+/, '').replace(/\/{2,}/g, '/');
	return p && !p.endsWith('/') ? `${p}/` : p;
}

export function parentPrefix(prefix: string): string {
	const parts = prefix.replace(/\/$/, '').split('/');
	parts.pop();
	return parts.length ? `${parts.join('/')}/` : '';
}

export const DO_REGIONS = ['nyc3', 'sfo3', 'sgp1', 'ams3', 'fra1', 'blr1', 'syd1', 'lon1', 'tor1', 'atl1'] as const;
