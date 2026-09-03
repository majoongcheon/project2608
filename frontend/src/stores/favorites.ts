// 즐겨찾기 — 마이페이지가 모아 보여 줄 기관 목록 (2026-09-03)
//
// **브라우저에만 둔다.** 이 서비스는 로그인이 없고(FR-002), 헌법 원칙 III 가
// 개인을 식별할 수 있는 보관을 금한다. 즐겨찾기를 서버에 두려면 "이 사람이
// 누구인지"를 서버가 알아야 하므로, 계정을 만들지 않는 한 서버에 둘 수 없다.
// 그래서 localStorage 다 — 기기를 옮기면 따라오지 않는다는 것을 화면에서
// 분명히 말해 준다(마이페이지 안내 문구).
//
// 저장하는 것은 화면에 다시 그릴 만큼의 최소 정보다. 기관 정보가 바뀌면
// 상세 화면에서 최신 값을 받아 오고, 여기 값은 목록에 이름을 띄우는 용도다.
import { defineStore } from 'pinia';
import { ref } from 'vue';

const KEY = 'cb.favorites';

export interface FavFacility {
  facilityId: number;
  name: string;
  phone: string | null;
  address: string | null;
  serviceTypes: string[];
  /** 언제 저장했는지 — 목록을 최근순으로 세운다 */
  savedAt: string;
}

function read(): FavFacility[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const v = JSON.parse(raw);
    return Array.isArray(v) ? v.filter((x) => x && typeof x.facilityId === 'number') : [];
  } catch {
    // 사생활 보호 모드·저장 공간 거부 등. 즐겨찾기가 없는 것으로 두고 계속 간다.
    return [];
  }
}

export const useFavoriteStore = defineStore('favorites', () => {
  const items = ref<FavFacility[]>(read());

  function persist() {
    try { localStorage.setItem(KEY, JSON.stringify(items.value)); } catch { /* noop */ }
  }

  const has = (id: number) => items.value.some((f) => f.facilityId === id);

  function add(f: Omit<FavFacility, 'savedAt'>) {
    if (has(f.facilityId)) return;
    items.value = [{ ...f, savedAt: new Date().toISOString() }, ...items.value];
    persist();
  }

  function remove(id: number) {
    items.value = items.value.filter((f) => f.facilityId !== id);
    persist();
  }

  /** 눌러서 켜고 끈다. 켜졌으면 true 를 돌려준다 */
  function toggle(f: Omit<FavFacility, 'savedAt'>): boolean {
    if (has(f.facilityId)) { remove(f.facilityId); return false; }
    add(f); return true;
  }

  return { items, has, add, remove, toggle };
});
