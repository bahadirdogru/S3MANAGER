// User-facing file operations shared by the toolbar, context menu and shortcuts.
import { open as openDialog } from '@tauri-apps/plugin-dialog';
import { toast } from 'svelte-sonner';
import { api, errorText, type Item } from '#lib/api.js';
import { toPrefix, uniqueCopyName } from '#lib/format.js';
import { dialogs, nameValidator } from '#lib/stores/dialogs.svelte.js';
import { explorer } from '#lib/stores/explorer.svelte.js';
import { transfers } from '#lib/stores/transfers.svelte.js';
import { ui } from '#lib/stores/ui.svelte.js';

function guard(label: string): boolean {
	if (ui.busy) {
		toast.warning(`Başka bir işlem devam ediyor: ${ui.busy}`);
		return false;
	}
	ui.busy = label;
	return true;
}

async function stage(paths: string[]) {
	if (!paths.length) return;
	try {
		const reqs = await api.expandUpload(paths, explorer.prefix);
		if (!reqs.length) return toast.info('Yüklenecek dosya bulunamadı');
		ui.upload = reqs;
	} catch (e) {
		toast.error(errorText(e));
	}
}

export async function pickUploadFiles() {
	const picked = await openDialog({ multiple: true, directory: false, title: 'Yüklenecek dosyaları seçin' });
	if (picked) await stage(Array.isArray(picked) ? picked : [picked]);
}

export async function pickUploadFolder() {
	const picked = await openDialog({ multiple: true, directory: true, title: 'Yüklenecek klasörü seçin' });
	if (picked) await stage(Array.isArray(picked) ? picked : [picked]);
}

export const uploadDropped = stage;

export async function download(items: Item[] = explorer.selectedItems) {
	if (!items.length) return toast.info('İndirilecek öğe seçilmedi');
	const dest = await openDialog({ directory: true, title: 'İndirme klasörünü seçin' });
	if (!dest || Array.isArray(dest)) return;
	try {
		const events = await api.startDownload(items, dest);
		if (!events.length) return toast.info('Klasör boş');
		transfers.add(events);
	} catch (e) {
		toast.error(errorText(e));
	}
}

export async function newFolder() {
	const name = await dialogs.prompt({
		title: 'Yeni Klasör',
		label: 'Klasör adı',
		confirmText: 'Oluştur',
		validate: nameValidator
	});
	if (!name) return;
	try {
		await api.createFolder(`${explorer.prefix}${name}/`);
		toast.success(`“${name}” oluşturuldu`);
		await explorer.refresh();
	} catch (e) {
		toast.error(errorText(e));
	}
}

export async function remove(items: Item[] = explorer.selectedItems) {
	if (!items.length) return;
	const folders = items.filter((i) => i.kind === 'folder').length;
	const ok = await dialogs.confirm({
		title: items.length === 1 ? `“${items[0].name}” silinsin mi?` : `${items.length} öğe silinsin mi?`,
		description:
			(folders ? 'Klasörler içindeki tüm dosyalarla birlikte silinir.\n' : '') + 'Bu işlem geri alınamaz.',
		confirmText: 'Sil',
		destructive: true
	});
	if (!ok || !guard('Silme')) return;
	const t = toast.loading('Siliniyor…');
	try {
		const n = await api.deleteItems(items);
		toast.success(`${n} nesne silindi`, { id: t });
		explorer.invalidate(explorer.prefix);
		await explorer.refresh();
	} catch (e) {
		toast.error(errorText(e), { id: t });
	} finally {
		ui.busy = null;
	}
}

export async function rename(item: Item | undefined = explorer.selectedItems[0]) {
	if (!item) return;
	if (explorer.selectedItems.length > 1) return toast.info('Yeniden adlandırmak için tek öğe seçin');
	const name = await dialogs.prompt({
		title: 'Yeniden Adlandır',
		label: 'Yeni ad',
		value: item.name,
		confirmText: 'Kaydet',
		validate: (v) =>
			nameValidator(v) ??
			(v.trim() !== item.name && explorer.items.some((i) => i.name === v.trim()) ? 'Bu adda bir öğe zaten var' : null)
	});
	if (!name || name === item.name || !guard('Yeniden adlandırma')) return;
	const t = toast.loading(`Yeniden adlandırılıyor: ${item.name}`);
	try {
		await api.renameItem(item, name);
		toast.success(`“${name}” olarak adlandırıldı`, { id: t });
		explorer.invalidate(explorer.prefix);
		await explorer.refresh();
	} catch (e) {
		toast.error(errorText(e), { id: t });
	} finally {
		ui.busy = null;
	}
}

async function transferWithin(kind: 'copy' | 'move', items: Item[]) {
	if (!items.length) return toast.info(kind === 'copy' ? 'Kopyalanacak öğe seçilmedi' : 'Taşınacak öğe seçilmedi');
	const input = await dialogs.prompt({
		title: kind === 'copy' ? 'Kopyala — Hedef Klasör' : 'Taşı — Hedef Klasör',
		label: 'Hedef klasör yolu',
		description:
			kind === 'copy'
				? 'Seçili öğeler bu klasöre kopyalanır. Boş bırakırsanız mevcut klasör kullanılır.'
				: 'Seçili öğeler bu klasöre taşınır.',
		value: explorer.prefix,
		placeholder: 'örn. yedek/2026/',
		confirmText: kind === 'copy' ? 'Kopyala' : 'Taşı'
	});
	if (input === null) return;
	const dest = toPrefix(input) || explorer.prefix;
	if (kind === 'move' && dest === explorer.prefix) return toast.info('Hedef mevcut klasörle aynı');
	if (!guard(kind === 'copy' ? 'Kopyalama' : 'Taşıma')) return;

	const verb = kind === 'copy' ? 'Kopyalanıyor' : 'Taşınıyor';
	const existing = new Set(explorer.items.map((i) => i.name));
	const t = toast.loading(`${verb}…`);
	let done = 0;
	try {
		for (const item of items) {
			toast.loading(`${verb} (${done + 1}/${items.length}): ${item.name}`, { id: t });
			// Copying into the same folder gets a "(kopya n)" name.
			const sameFolder = dest === explorer.prefix;
			const name = kind === 'copy' && sameFolder ? uniqueCopyName(item.name, existing) : item.name;
			existing.add(name);
			const target = item.kind === 'folder' ? `${dest}${name}/` : `${dest}${name}`;
			if (kind === 'copy') await api.copyItem(item, target);
			else await api.moveItem(item, target);
			done++;
		}
		toast.success(`${done} öğe ${kind === 'copy' ? 'kopyalandı' : 'taşındı'}`, { id: t });
	} catch (e) {
		toast.error(`${done}/${items.length} tamamlandı — ${errorText(e)}`, { id: t });
	} finally {
		ui.busy = null;
		explorer.invalidate(dest);
		explorer.invalidate(explorer.prefix);
		await explorer.refresh();
	}
}

export const copyTo = (items: Item[] = explorer.selectedItems) => transferWithin('copy', items);
export const moveTo = (items: Item[] = explorer.selectedItems) => transferWithin('move', items);

export function share(item: Item | undefined = explorer.selectedItems[0], days: 3 | 7 = 3) {
	if (item?.kind === 'file') ui.share = { item, days };
}

export function properties(item: Item | undefined = explorer.selectedItems[0]) {
	if (item?.kind === 'file') ui.properties = item;
}
