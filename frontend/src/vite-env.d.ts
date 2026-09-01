/// <reference types="vite/client" />
declare module '*.vue' {
  import type { DefineComponent } from 'vue';
  const c: DefineComponent<{}, {}, any>;
  export default c;
}
interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
  readonly VITE_KAKAO_MAP_KEY?: string;
}
interface ImportMeta { readonly env: ImportMetaEnv }
